from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

class DueDateGeneratorWizard(models.TransientModel):
    _name = 'property.due.date.generator.wizard'
    _description = 'Generate Due Dates for Installments'

    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True, readonly=True)
    start_payment_line_id = fields.Many2one(
        'property.payment.line',
        string="Start From Installment",
        required=True,
        domain="[('sale_id', '=', sale_id)]",
        help="Select the first installment where the new dates should begin."
    )
    start_date = fields.Date(string="First Due Date", required=True, default=fields.Date.context_today)
    
    interval_type = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly')
    ], string="Increment Type", default='month', required=True)

    interval_duration = fields.Integer(
        string="Number of Months",
        default=1,
        help="Specify how many months to increment by."
    )

    summary_html = fields.Html(string="Summary", compute='_compute_summary_html')


    @api.constrains('interval_type', 'interval_duration')
    def _check_interval_duration(self):
        for wiz in self:
            if wiz.interval_type == 'month' and wiz.interval_duration <= 0:
                raise ValidationError(_("Number of months must be greater than 0."))

    @api.depends('start_payment_line_id', 'interval_type', 'start_date', 'sale_id', 'interval_duration')
    def _compute_summary_html(self):
        for wiz in self:
            if not all([wiz.start_payment_line_id, wiz.interval_type, wiz.start_date, wiz.sale_id]):
                wiz.summary_html = "<p><i>Please select a start installment, date, and interval.</i></p>"
                continue

            lines = self.env['property.payment.line'].search(
                [('sale_id', '=', wiz.sale_id.id)],
                order='sequence asc, id asc'
            )
            
            start_idx = -1
            for i, line in enumerate(lines):
                if line.id == wiz.start_payment_line_id.id:
                    start_idx = i
                    break

            if start_idx == -1:
                wiz.summary_html = ""
                continue
                
            affected_count = len(lines) - start_idx
            interval_label = f"{wiz.interval_duration} month(s)" if wiz.interval_type == 'month' else wiz.interval_type
            wiz.summary_html = f"""
                <div class="alert alert-info" role="alert">
                    <b>Action Summary:</b><br/>
                    This action will update the due dates for <b>{affected_count}</b> installment(s), starting from <b>{wiz.start_payment_line_id.display_name}</b>.<br/>
                    The date will increment <b>{interval_label}</b> starting from <b>{wiz.start_date}</b> based on the installment sequence order.
                </div>
            """

    def action_confirm(self):
        self.ensure_one()
        lines = self.env['property.payment.line'].search(
            [('sale_id', '=', self.sale_id.id)],
            order='sequence asc, id asc'
        )

        start_idx = -1
        for i, line in enumerate(lines):
            if line.id == self.start_payment_line_id.id:
                start_idx = i
                break

        if start_idx == -1:
            return {'type': 'ir.actions.act_window_close'}

        current_date = self.start_date
        for i in range(start_idx, len(lines)):
            lines[i].due_date = current_date
            
            if self.interval_type == 'month':
                current_date += relativedelta(months=self.interval_duration)
            elif self.interval_type == 'quarter':
                current_date += relativedelta(months=3)
            elif self.interval_type == 'year':
                current_date += relativedelta(years=1)

        self.sale_id.message_post(body=Markup(f"<b>Due Dates Updated</b> - Sequence starting from {self.start_payment_line_id.display_name} with {self.interval_type} intervals."))
        return {'type': 'ir.actions.act_window_close'}