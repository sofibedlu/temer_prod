from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    due_date = fields.Date(string="Due Date")

    is_fully_paid = fields.Boolean(
        string="Is Fully Paid",
        compute="_compute_is_fully_paid",
        store=False
    )

    @api.depends('expected_amount', 'paid_amount')
    def _compute_is_fully_paid(self):
        for rec in self:
            rec.is_fully_paid = (rec.expected_amount > 0 and rec.paid_amount >= rec.expected_amount)

    @api.onchange('expected')
    def _onchange_expected_percentage(self):
        for rec in self:
            price = rec.sale_id.new_sale_price or rec.sale_id.sale_price
            if price:
                rec.expected_amount = rec.expected * price / 100.0

    @api.onchange('expected_amount')
    def _onchange_expected_amount(self):
        for rec in self:
            price = rec.sale_id.new_sale_price or rec.sale_id.sale_price
            if price:
                rec.expected = (rec.expected_amount / price) * 100.0
    
    @api.onchange('paid_amount', 'expected_amount')
    def _onchange_paid_status_clear_date(self):
        for rec in self:
            if rec.expected_amount > 0 and rec.paid_amount >= rec.expected_amount:
                 rec.due_date = False

    @api.depends('expected_amount', 'paid_amount', 'discount')
    def compute_remaining_amount(self):
        for rec in self:
            rec.remaining = rec.expected_amount - rec.paid_amount - rec.discount

class PropertySale(models.Model):
    _inherit = 'property.sale'

    payment_schedule_type = fields.Selection(
        [('progress', 'Progress Based'), ('time', 'Time Based')],
        string="Payment Schedule Type",
        default='progress',
        required=True
    )
    has_custom_schedule = fields.Boolean(
        string="Has Custom Schedule",
        default=False,
        help="If enabled, the installment lines are managed manually/by wizard and must not be regenerated from Payment Term."
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PropertySale, self).create(vals_list)
        for sale in records:
            # clear any default due dates
            if sale.payment_schedule_type == 'progress':
                sale.payment_installment_line_ids.write({'due_date': False})
        return records

    def write(self, vals):
        res = super(PropertySale, self).write(vals)
        if vals.get('payment_schedule_type') == 'progress':
            for sale in self:
                sale.has_custom_schedule = False
                
                # Clear all due dates on the installment lines
                sale.payment_installment_line_ids.write({'due_date': False})
        return res

    @api.constrains('payment_schedule_type', 'payment_installment_line_ids')
    def _check_time_based_due_dates(self):
        for sale in self:
            if sale.payment_schedule_type == 'time':
                for line in sale.payment_installment_line_ids:
                    is_paid = line.expected_amount > 0 and line.paid_amount >= line.expected_amount
                    
                    if not line.due_date and not is_paid:
                        raise ValidationError(_(
                            "Please set a Due Date for all unpaid payment installments when the schedule type is 'Time Based'."
                        ))

    def action_open_schedule_generator(self):
        """Open the wizard to generate lines for the sale"""
        return {
            'name': 'Generate Payment Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'property.legacy.schedule.generator',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_id': self.id,
                'default_amount': self.sale_price / 12
            }
        }

    def compute_sale_payment_line(self):
        allowed = self.filtered(lambda s: not (s.payment_schedule_type == 'time' or s.has_custom_schedule))
        if not allowed:
            return
        return super(PropertySale, allowed).compute_sale_payment_line()

    def create_payment_term_line(self, sale_id, payment_term, reservation_id, sale_price, res):
        sale_db = self.browse(sale_id)
        schedule_type = getattr(res, 'payment_schedule_type', False) or sale_db.payment_schedule_type
        has_custom = bool(getattr(res, 'has_custom_schedule', False) or sale_db.has_custom_schedule)

        if schedule_type == 'time' or has_custom:
            return

        return super().create_payment_term_line(sale_id, payment_term, reservation_id, sale_price, res)

    @api.onchange('payment_schedule_type')
    def _onchange_payment_schedule_type(self):
        for sale in self:
            if sale.payment_schedule_type == 'progress':
                sale.has_custom_schedule = False

                # Recalculate based on payment term
                sale.recalculate_payment_line_based_on_payment_term()

                # Clear due dates in UI 
                for line in sale.payment_installment_line_ids:
                    line.due_date = False