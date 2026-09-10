from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_approval_state = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved')],
        string='Payment Approval State',
        default='draft',
        copy=False,
        tracking=True
    )
    approved_by_id = fields.Many2one(
        'res.users', 
        string='Approved By', 
        copy=False, 
        tracking=True
    )

    def action_approve_for_payment(self):
        for move in self:
            if move.state != 'posted':
                raise UserError(_("You can only approve posted bills for payment."))
            move.payment_approval_state = 'approved'
            move.approved_by_id = self.env.user.id

    def action_register_payment(self):
        for move in self:
            if move.move_type == 'in_invoice' and move.payment_approval_state != 'approved':
                raise UserError(_("You must approve this vendor bill for payment before registering a payment."))
        return super(AccountMove, self).action_register_payment()