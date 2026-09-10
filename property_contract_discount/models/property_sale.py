from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError

class PropertySale(models.Model):
    _inherit = 'property.sale'

    installment_discount_total = fields.Monetary(
        string="Total Line Discount",
        currency_field='currency_id',
        compute='_compute_installment_discount_total',
        store=True,
        help="Sum of discounts applied directly to installment lines."
    )

    @api.depends('payment_installment_line_ids.discount')
    def _compute_installment_discount_total(self):
        for rec in self:
            rec.installment_discount_total = sum(rec.payment_installment_line_ids.mapped('discount'))

    def action_open_custom_discount_wizard(self):
        self.ensure_one()
        return {
            'name': 'Apply Discount',
            'type': 'ir.actions.act_window',
            'res_model': 'property.apply.discount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_id': self.id,
            }
        }
    
    def _create_collection_order(self):
        collection = super(PropertySale, self)._create_collection_order()
        if collection:
            collection.write({
                'total_discount': self.installment_discount_total
            })
        
        return collection

    @api.depends('payment_installment_line_ids.expected_amount', 'payment_installment_line_ids.discount', 'sale_price', 'new_sale_price')
    def _compute_is_total_amount_mismatched(self):
        for sale in self:
            if not sale.payment_installment_line_ids:
                try:
                    super(PropertySale, sale)._compute_is_total_amount_mismatched()
                except:
                    pass
                continue

            total_scheduled = sum(line.expected_amount + (line.discount or 0.0) for line in sale.payment_installment_line_ids)
            target_price = sale.new_sale_price if sale.new_sale_price else sale.sale_price
            
            if float_compare(total_scheduled, target_price, precision_digits=2) != 0:
                sale.is_total_amount_mismatched = True
                diff = total_scheduled - target_price
                sale.amount_mismatch_warning = _(
                    "Warning: The sum of installments (Net + Discount) (%(total)s) does not match the Sales Price (%(price)s). Difference: %(diff)s"
                ) % {
                    'total': round(total_scheduled, 2), 
                    'price': round(target_price, 2), 
                    'diff': round(diff, 2)
                }
            else:
                sale.is_total_amount_mismatched = False
                sale.amount_mismatch_warning = False

    def _validate_installment_totals_after_save(self):
        """ Validate based on (Expected + Discount) """
        for sale in self:
            target_price = sale.new_sale_price if sale.new_sale_price else sale.sale_price
            
            if not sale.payment_installment_line_ids or target_price == 0:
                continue

            total_scheduled = sum(line.expected_amount + (line.discount or 0.0) for line in sale.payment_installment_line_ids)
            
            if float_compare(total_scheduled, target_price, precision_digits=2) != 0:
                raise ValidationError(_(
                    "Validation Error: The sum of payment installments (plus discounts) must equal the Sales Price.\n"
                    "Total (Net+Disc): %s\nSales Price: %s\nDifference: %s"
                ) % (total_scheduled, target_price, total_scheduled - target_price))


class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    _rec_name = 'payment_term_id'

    expected_is_net = fields.Boolean(
        default=False,
        help="If enabled, expected_amount is considered the Net amount (after discount). "
             "Used to adjust remaining amount and percentage calculations."
    )

    @api.depends('expected', 'sale_id.new_sale_price', 'sale_id.sale_price', 'discount', 'expected_is_net')
    def compute_expected_amount(self):
        for rec in self:
            price = rec.sale_id.new_sale_price or rec.sale_id.sale_price or 0.0
            if rec.payment_term_id and getattr(rec.payment_term_id, 'payment_type', False) == 'fixed':
                gross_amount = getattr(rec.payment_term_id, 'amount', 0.0)
            else:
                gross_amount = (rec.expected * price) / 100.0
            if rec.expected_is_net:
                rec.expected_amount = gross_amount - (rec.discount or 0.0)
            else:
                rec.expected_amount = gross_amount

    @api.onchange('expected_amount')
    def _onchange_expected_amount(self):
        for rec in self:
            price = rec.sale_id.new_sale_price or rec.sale_id.sale_price
            if price:
                gross_amount = rec.expected_amount + (rec.discount or 0.0)
                rec.expected = (gross_amount / price) * 100.0

    @api.onchange('expected')
    def _onchange_expected_percentage(self):
        for rec in self:
            price = rec.sale_id.new_sale_price or rec.sale_id.sale_price
            if price:
                gross_amount = rec.expected * price / 100.0
                rec.expected_amount = gross_amount - (rec.discount or 0.0)

    @api.depends('expected_amount', 'paid_amount', 'discount', 'expected_is_net')
    def compute_remaining_amount(self):
        for rec in self:
            if rec.expected_is_net:
                rec.remaining = (rec.expected_amount or 0.0) - (rec.paid_amount or 0.0)
            else:
                rec.remaining = (rec.expected_amount or 0.0) - (rec.paid_amount or 0.0) - (rec.discount or 0.0)

    @api.depends('expected', 'expected_amount', 'paid_amount', 'discount', 'expected_is_net')
    def compute_payment_status(self):
        for rec in self:
            if rec.expected_is_net:
                exp = rec.expected_amount or 0.0
                paid = rec.paid_amount or 0.0
                
                if paid >= exp and exp > 0:
                    rec.state = "paid"
                elif exp == 0 and paid == 0 and (rec.discount or 0.0) > 0:
                    rec.state = "discounted"
                elif paid > 0:
                    rec.state = "partial"
                else:
                    rec.state = "not_paid"
            else:
                super(PropertyPaymentLine, rec).compute_payment_status()