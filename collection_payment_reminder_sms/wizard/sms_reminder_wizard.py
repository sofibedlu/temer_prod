from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SmsReminderWizard(models.TransientModel):
    _name = 'collection.sms.reminder.wizard'
    _description = 'Batch SMS Reminder Wizard'

    date_from = fields.Date(string="Due Date From", required=True)
    date_to = fields.Date(string="Due Date To", required=True)
    template_id = fields.Many2one(
        'collection.sms.template', 
        string="SMS Template", 
        required=True, 
        domain="[('template_type', '=', 'first')]"
    )
    line_ids = fields.One2many('collection.sms.reminder.wizard.line', 'wizard_id', string="Installments")

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        if self.date_from and self.date_to:
            installments = self.env['collection.installment'].search([
                ('due_date', '>=', self.date_from),
                ('due_date', '<=', self.date_to),
                ('state', '=', 'unpaid'),
                ('collection_id.state', '=', 'active'),
                ('reminder_stage', '=', '0')
            ])

            lines = [(5, 0, 0)]
            for inst in installments:
                lines.append((0, 0, {'installment_id': inst.id, 'is_selected': True}))
            self.line_ids = lines

    def action_send_reminders(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        if not selected_lines:
            raise UserError(_("Please select at least one installment."))

        sent_count = 0
        for line in selected_lines:
            inst = line.installment_id
            success = inst._send_sms_from_template(inst, self.template_id)
            if success and self.template_id.template_type == 'first':
                # Arm the automation!
                inst.write({'reminder_stage': '1'})
            sent_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'First Reminders Dispatched',
                'message': f"Sent {sent_count} SMS messages. Automation is now set for 2nd and 3rd reminders.",
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

class SmsReminderWizardLine(models.TransientModel):
    _name = 'collection.sms.reminder.wizard.line'
    _description = 'SMS Reminder Wizard Line'

    wizard_id = fields.Many2one('collection.sms.reminder.wizard')
    is_selected = fields.Boolean(string="Send", default=True)
    installment_id = fields.Many2one('collection.installment', string="Installment", required=True)
    partner_id = fields.Many2one(related='installment_id.partner_id', string="Customer")
    due_date = fields.Date(related='installment_id.due_date')
    amount_residual = fields.Monetary(related='installment_id.amount_residual', string="Remaining", currency_field='currency_id')
    currency_id = fields.Many2one(related='installment_id.currency_id')
    phone = fields.Char(related='partner_id.mobile', string="Phone")
    # 🌟 NEW: Dynamic Customer Name
    customer_name = fields.Char(string="Customer Name", compute="_compute_customer_name")

    @api.depends('installment_id.collection_id.buyers_name_text', 'installment_id.partner_id.name')
    def _compute_customer_name(self):
        for rec in self:
            b_text = rec.installment_id.collection_id.buyers_name_text
            if b_text and b_text.strip() != 'No buyers found':
                rec.customer_name = b_text
            else:
                rec.customer_name = rec.installment_id.partner_id.name