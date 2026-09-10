from odoo import models, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def create_payment_term_line(self, sale_id, payment_term, reservation_id, sale_price, res):
        result = super(PropertySale, self).create_payment_term_line(
            sale_id, payment_term, reservation_id, sale_price, res
        )
        sale = self.browse(sale_id)
        if sale.payment_installment_line_ids:
            non_standard_lines = sale.payment_installment_line_ids.filtered(
                lambda l: l.payment_term_id and not l.payment_term_id.is_standard
            )
            if non_standard_lines:
                non_standard_lines.unlink()

        return result

    def create_sale_payment_term(self, discounts, total_payment, res):
        result = super(PropertySale, self).create_sale_payment_term(discounts, total_payment, res)
        if res.payment_installment_line_ids:
            non_standard_lines = res.payment_installment_line_ids.filtered(
                lambda l: l.payment_term_id and not l.payment_term_id.is_standard
            )
            if non_standard_lines:
                non_standard_lines.unlink()
                
        return result