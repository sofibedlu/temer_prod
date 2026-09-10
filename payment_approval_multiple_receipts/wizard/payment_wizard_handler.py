from odoo import models, _
from odoo.exceptions import UserError

class PaymentWizardHandler(models.TransientModel):
    _inherit = 'property.payment.register.wizard'

    def _validate_amount_and_discount(self):
        """allow multiple pending payments and check against residual - pending."""
        self.ensure_one()

        installment = self.installment_id
        if not installment:
            return

        residual = installment.amount_residual or 0.0
        pending = installment.pending_approval_amount or 0.0
        available_to_pay = residual - pending

        if self.amount <= 0:
            raise UserError(_("Payment amount must be greater than zero."))
        
        if available_to_pay >= 0 and self.amount > available_to_pay:
            raise UserError(
                _("You cannot pay %(amount)s. The remaining amount (after %(pending)s pending payments) is only %(available)s.") % {
                    'amount': self.amount,
                    'pending': pending,
                    'available': available_to_pay,
                }
            )

        if self.apply_discount and self.discount_percentage > 0:
            config = self.env['collection.discount.config'].sudo().search([], limit=1)
            max_percent = config.max_manual_discount_percentage if config else 10.0
            
            if self.discount_percentage > max_percent:
                 raise UserError(_("You cannot apply a discount of %s%%. The maximum allowed is %s%%.") % (self.discount_percentage, max_percent))