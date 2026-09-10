from odoo import models, _
from odoo.exceptions import UserError

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    def action_open_payment_wizard(self):
        """
        block the user from proceeding with payment until
        the request is approved or rejected.
        """
        for rec in self:
            pending_requests = self.env['discount.request'].search([
                ('installment_id', '=', rec.id),
                ('state', '=', 'pending')
            ], limit=1)
            
            if pending_requests:
                raise UserError(_(
                    "You cannot register a payment for installment '%s' because it has a pending discount request. "
                    "Please wait for the request to be approved or rejected before proceeding." % rec.name
                ))
                
        return super(CollectionInstallment, self).action_open_payment_wizard()
