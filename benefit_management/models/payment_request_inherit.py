from odoo import models, fields, api, _

class PaymentRequest(models.Model):
    _inherit = 'payment.request'

    # 🌟 Add Employee to pay_to selection
    pay_to = fields.Selection(
        selection_add=[('employee', 'Employee')],
        ondelete={'employee': lambda recs: recs.write({'pay_to': 'vendor'})}
    )


class PaymentOrder(models.Model):
    _inherit = 'payment.order'

    # 🌟 Add Employee to pay_to selection
    pay_to = fields.Selection(
        selection_add=[('employee', 'Employee')],
        ondelete={'employee': lambda recs: recs.write({'pay_to': 'vendor'})}
    )

    def action_confirm(self):
        """
        When confirming a payment order for an Employee, ensure the resulting 
        account.payment is an Outbound payment (Send Money) to the employee contact.
        """
        res = super().action_confirm()
        for rec in self.filtered(lambda p: p.pay_to == 'employee' and p.account_payment_id):
            rec.account_payment_id.write({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
            })
        return res