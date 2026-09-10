from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

class PropertySale(models.Model):
    _inherit = 'property.sale'

    @api.onchange('property_payment_term')
    def recalculate_payment_line_based_on_payment_term(self):
        for rec in self:
            if not rec.property_payment_term:
                return

            if getattr(rec, 'has_custom_schedule', False):
                return

            sale = rec._origin if rec._origin and rec._origin.id else rec
            if not sale.id:
                return

            if sale.property_payment_term.id != rec.property_payment_term.id:
                sale.sudo().write({'property_payment_term': rec.property_payment_term.id})

            if hasattr(sale, 'compute_sale_payment_line'):
                sale.compute_sale_payment_line()
            else:
                # Fallback to base flow
                self.env['property.payment.line'].sudo().search([('sale_id', '=', sale.id)]).unlink()
                reservation_id = sale.reservation_id.id if getattr(sale, 'reservation_id', False) else False
                sale_price_base = (sale.sale_price - (sale.discount or 0.0)) or 0.0
                sale.create_payment_term_line(sale.id, sale.property_payment_term, reservation_id, sale_price_base, sale)
                sale.add_discount_on_payment_term(sale)
                sale.add__special_discount_on_payment_term(sale)

            new_lines = self.env['property.payment.line'].sudo().search(
                [('sale_id', '=', sale.id)],
                order='sequence asc, id asc'
            )
            rec.payment_installment_line_ids = new_lines

    # @api.constrains('payment_installment_line_ids', 'reservation_id', 'state')
    # def _check_total_paid_matches_reservation_downpayment(self):
    #     """
    #     prevent total paid on sale from being different than the 
    #     one recorded on the reservation.
    #     """
    #     for rec in self:
    #         if rec.state not in ['confirm', 'request_for_confirm']:
    #             continue
            
    #         if not getattr(rec, "reservation_id", False) or not rec.reservation_id:
    #             continue

    #         res_payments = rec.reservation_id.payment_line_ids.filtered(
    #             lambda p: getattr(p, "payment_status", False) != "canceled"
    #         )
    #         reservation_paid = sum(res_payments.mapped("amount") or [0.0])
    #         sale_paid = sum(rec.payment_installment_line_ids.mapped("paid_amount") or [0.0])
    #         rounding = 0.01
    #         if getattr(rec, "company_id", False) and rec.company_id.currency_id:
    #             rounding = rec.company_id.currency_id.rounding or 0.01

    #         if float_compare(sale_paid, reservation_paid, precision_rounding=rounding) != 0:
    #             raise ValidationError(_(
    #                 "You cannot save this Sale because the Paid amount on the Sale (%.2f) "
    #                 "must match the Reservation downpayment (%.2f).\n\n"
    #                 "Please adjust the installment 'Paid Amount' values."
    #             ) % (sale_paid, reservation_paid))
            
    def action_confirm(self):
        for sale in self:
            if not sale.template_id:
                raise ValidationError(_("Please select Contract Template before confirming the Sale."))
            if not sale.template_id.developer_id or not sale.template_id.developer_id.sequence:
                raise ValidationError(_("Contract Template is missing Developer/Sequence configuration."))

        ContractApp = self.env["contract.application"]
        for sale in self:
            contract = sale.contract_id[:1] if hasattr(sale, "contract_id") else ContractApp.search(
                [("property_sale_id", "=", sale.id)], limit=1
            )
            if not contract:
                contract = ContractApp.create({"property_sale_id": sale.id})

            if contract.contract_date_char is False:
                if hasattr(contract, "_get_default_ethiopian_date"):
                    contract.contract_date_char = contract._get_default_ethiopian_date() or ""
                else:
                    contract.contract_date_char = ""

        return super().action_confirm()
    

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    @api.depends('expected', 'expected_amount', 'paid_amount', 'discount')
    def compute_payment_status(self):
        for rec in self:
            paid = rec.paid_amount + rec.discount
            cmp_result = float_compare(paid, rec.expected_amount, precision_digits=2)
            
            if cmp_result >= 0: # paid >= expected_amount
                if rec.paid_amount == 0 and rec.discount > 0:
                    rec.state = "discounted"
                else:
                    rec.state = "paid"
            elif rec.paid_amount > 0 and cmp_result < 0: # paid < expected_amount
                rec.state = "partial"
            else:
                rec.state = "not_paid"
