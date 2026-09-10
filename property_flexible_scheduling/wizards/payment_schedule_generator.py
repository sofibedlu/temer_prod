from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class PaymentScheduleGenerator(models.TransientModel):
    _name = 'property.legacy.schedule.generator'
    _description = 'Generate Flexible Payment Schedule'

    legacy_sale_id = fields.Many2one('property.legacy.sale', string="Legacy Sale")
    sale_id = fields.Many2one('property.sale', string="Property Sale")
    generation_mode = fields.Selection(
        [
            ('append', 'Append'),
            ('replace_unpaid', 'Replace Unpaid Only'),
            ('replace_all', 'Replace All'),
        ],
        string="Generation Mode",
        default='append',
        required=True,
    )

    amount = fields.Float(string="Amount Per Installment", required=True)
    start_date = fields.Date(string="First Payment Date", required=True, default=fields.Date.today)
    number_of_installments = fields.Integer(string="Number of Installments", default=12)
    interval_type = fields.Selection([
        ('month', 'Months'),
        ('quarter', 'Quarterly'),
        ('year', 'Years')
    ], string="Interval", default='month')
    
    description_prefix = fields.Char(string="Description Prefix", default="Installment")

    def action_generate_lines(self):
        """Generate lines for either Legacy Sale or Normal Sale"""
        current_date = self.start_date
        if self.legacy_sale_id:
            lines_to_create = []
            for i in range(self.number_of_installments):
                next_date = self._get_next_date(current_date, i)
                lines_to_create.append({
                    'legacy_sale_id': self.legacy_sale_id.id,
                    'name': f"{self.description_prefix} {i + 1}/{self.number_of_installments}",
                    'amount': self.amount,
                    'due_date': next_date,
                    'status': 'unpaid'
                })
            self.env['property.legacy.sale.line'].create(lines_to_create)

        elif self.sale_id:
            sale = self.sale_id
            sale.write({'payment_schedule_type': 'time', 'has_custom_schedule': True})
            if self.generation_mode == 'replace_all':
                sale.payment_installment_line_ids.unlink()

            elif self.generation_mode == 'replace_unpaid':
                def _is_unpaid(line):
                    state = getattr(line, 'state', False)
                    paid_amount = line.paid_amount or 0.0
                    if state:
                        return state in ('not_paid', 'unpaid')
                    return paid_amount == 0.0

                sale.payment_installment_line_ids.filtered(_is_unpaid).unlink()

            price = sale.sale_price or 0.0
            pct = ((self.amount / price) * 100.0) if price else 0.0
            lines_to_create = []
            for i in range(self.number_of_installments):
                next_date = self._get_next_date(current_date, i)
                name = f"{self.description_prefix} {i + 1}/{self.number_of_installments}"
                term_line = self.env['property.payment.term.line'].create({
                    'name': name,
                    'amount': self.amount,
                    'percentage': 0.0,
                })

                lines_to_create.append({
                    'sale_id': sale.id,
                    'payment_term_id': term_line.id,
                    'due_date': next_date,
                    'expected_amount': self.amount,
                    'expected': pct,
                    'paid_amount': 0.0,
                })

            self.env['property.payment.line'].create(lines_to_create)
            return {'type': 'ir.actions.act_window_close'}

        return {'type': 'ir.actions.act_window_close'}

    def _get_next_date(self, start_date, i):
        if self.interval_type == 'month':
            return start_date + relativedelta(months=i)
        elif self.interval_type == 'quarter':
            return start_date + relativedelta(months=i*3)
        else:
            return start_date + relativedelta(years=i)