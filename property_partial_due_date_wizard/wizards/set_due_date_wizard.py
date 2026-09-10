from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date

class PropertySetDueDateWizard(models.TransientModel):
    _name = 'property.set.due.date.wizard'
    _description = 'Set Due Date for Partial Payment Line'

    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True, readonly=True)
    available_payment_line_ids = fields.Many2many(
        'property.payment.line',
        compute='_compute_available_payment_line_ids'
    )
    payment_line_id = fields.Many2one(
        'property.payment.line',
        string='Payment Line',
        required=True
    )
    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        currency_field='currency_id',
        compute='_compute_remaining_amount',
        readonly=True
    )
    currency_id = fields.Many2one('res.currency', related='sale_id.currency_id', readonly=True)
    new_due_date = fields.Date(string='New Due Date', required=True)
    due_days_count = fields.Integer(compute='_compute_due_days_count', string="Days Until Due")

    @api.depends('sale_id')
    def _compute_available_payment_line_ids(self):
        for rec in self:
            valid_lines = rec.sale_id.payment_installment_line_ids.filtered(
                lambda l: l.state != 'paid'
            )
            rec.available_payment_line_ids = valid_lines.ids

    @api.depends('new_due_date')
    def _compute_due_days_count(self):
        today = fields.Date.today()
        for rec in self:
            if rec.new_due_date:
                delta = (rec.new_due_date - today).days
                rec.due_days_count = delta if delta > 0 else 0
            else:
                rec.due_days_count = 0

    @api.depends('payment_line_id')
    def _compute_remaining_amount(self):
        for rec in self:
            if rec.payment_line_id:
                rec.remaining_amount = rec.payment_line_id.expected_amount - rec.payment_line_id.paid_amount
            else:
                rec.remaining_amount = 0.0

    def action_confirm(self):
        if not self.payment_line_id:
            raise UserError(_("Please select a payment line."))
            
        if self.payment_line_id.state == 'paid':
            raise UserError(_("This payment line is already fully paid."))

        self.payment_line_id.write({'due_date': self.new_due_date})
        line_name = self.payment_line_id.payment_term_id.name if hasattr(self.payment_line_id, 'payment_term_id') and self.payment_line_id.payment_term_id else self.payment_line_id.display_name
        
        self.sale_id.message_post(
            body=_("Due date set for payment line '%s' to %s (remaining: %.2f)") % (
                line_name, self.new_due_date, self.remaining_amount
            )
        )
        return {'type': 'ir.actions.act_window_close'}
    

class PropertySale(models.Model):
    _inherit = 'property.sale'

    has_partial_due_date = fields.Boolean(
        compute='_compute_has_partial_due_date',
        string="Has Partial Due Date"
    )

    @api.depends('payment_installment_line_ids.due_date')
    def _compute_has_partial_due_date(self):
        for sale in self:
            sale.has_partial_due_date = any(line.due_date for line in sale.payment_installment_line_ids)

    def action_open_set_due_date_wizard(self):
        return {
            'name': 'Set Due Date for Partial Payment Line',
            'type': 'ir.actions.act_window',
            'res_model': 'property.set.due.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id}
        }
    
    def _create_collection_order(self):

        collection = super(PropertySale, self)._create_collection_order()

        if getattr(self, 'payment_schedule_type', False) == 'progress':
            for line in self.payment_installment_line_ids:
                if line.due_date and hasattr(line, 'payment_term_id'):
                    installment = collection.installment_ids.filtered(
                        lambda i: i.payment_term_line_id.id == line.payment_term_id.id
                    )
                    if installment:
                        installment.write({
                            'due_date': line.due_date,
                            'is_progress_based': True
                        })
        return collection