from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sync_pre_contract_refund_payment_status(self):
        paid_moves = self.filtered(
            lambda move: move.payment_state in ('paid', 'in_payment')
        )
        if not paid_moves:
            return
        refunds = self.env['property.pre.contract.refund'].sudo().search([
            ('credit_note_id', 'in', paid_moves.ids),
            ('state', '=', 'approved'),
        ])
        refunds._mark_paid_from_credit_note()

    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        self._sync_pre_contract_refund_payment_status()
        return res
