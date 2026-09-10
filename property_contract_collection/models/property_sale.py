from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError

class PropertySale(models.Model):
    _inherit = 'property.sale'

    is_total_amount_mismatched = fields.Boolean(
        string="Total Mismatched",
        compute="_compute_is_total_amount_mismatched",
        store=False
    )
    
    amount_mismatch_warning = fields.Char(
        string="Mismatch Warning",
        compute="_compute_is_total_amount_mismatched",
        store=False
    )

    @api.depends('payment_installment_line_ids.expected_amount', 'sale_price', 'new_sale_price')
    def _compute_is_total_amount_mismatched(self):
        for sale in self:
            if not sale.payment_installment_line_ids:
                sale.is_total_amount_mismatched = False
                sale.amount_mismatch_warning = False
                continue

            total_scheduled = sum(sale.payment_installment_line_ids.mapped('expected_amount'))
            target_price = sale.new_sale_price if sale.new_sale_price else sale.sale_price
            
            if float_compare(total_scheduled, target_price, precision_digits=2) != 0:
                sale.is_total_amount_mismatched = True
                diff = total_scheduled - target_price
                sale.amount_mismatch_warning = _(
                    "Warning: The sum of installments (%(total)s) does not match the Sales Price (%(price)s). Difference: %(diff)s"
                ) % {
                    'total': round(total_scheduled, 2), 
                    'price': round(target_price, 2), 
                    'diff': round(diff, 2)
                }
            else:
                sale.is_total_amount_mismatched = False
                sale.amount_mismatch_warning = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PropertySale, self).create(vals_list)
        records._validate_installment_totals_after_save()
        return records

    def write(self, vals):
        res = super(PropertySale, self).write(vals)
        if 'payment_installment_line_ids' in vals or 'sale_price' in vals or 'new_sale_price' in vals:
            self._validate_installment_totals_after_save()
        return res

    def _validate_installment_totals_after_save(self):
        for sale in self:
            target_price = sale.new_sale_price if sale.new_sale_price else sale.sale_price
            
            if not sale.payment_installment_line_ids or target_price == 0:
                continue

            total_scheduled = sum(line.expected_amount for line in sale.payment_installment_line_ids)
            if float_compare(total_scheduled, target_price, precision_digits=2) != 0:
                raise ValidationError(_(
                    "Validation Error: The sum of payment installments must equal the Sales Price.\n"
                    "Please adjust the installment amounts before saving."
                ))


class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence', 
        default=10, 
        store=True, 
        related=False, 
        readonly=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sequence' not in vals:
                term_seq = 10
                if vals.get('payment_term_id'):
                    term_line = self.env['property.payment.term.line'].browse(vals['payment_term_id'])
                    if term_line:
                        term_seq = term_line.sequence
                
                # auto-increment based on existing sale lines
                if term_seq == 10 and vals.get('sale_id'):
                    existing_lines = self.env['property.payment.line'].search([('sale_id', '=', vals['sale_id'])])
                    max_seq = max(existing_lines.mapped('sequence')) if existing_lines else 0
                    vals['sequence'] = max(9, max_seq) + 1
                else:
                    vals['sequence'] = term_seq

        return super().create(vals_list)