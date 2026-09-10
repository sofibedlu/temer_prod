from odoo import models


class PaymentWizardHandler(models.TransientModel):
    _inherit = "property.payment.register.wizard"

    def action_confirm_payment(self):
        self.ensure_one()
        wiz = self.with_context(payment_requested_by_uid=self.env.uid)
        return super(PaymentWizardHandler, wiz).action_confirm_payment()