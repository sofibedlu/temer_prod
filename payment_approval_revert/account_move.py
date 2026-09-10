from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self._revert_collection_payments()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self._revert_collection_payments()
        return res

    def unlink(self):
        self._revert_collection_payments()
        return super(AccountMove, self).unlink()

    def _revert_collection_payments(self):
        for move in self:
            if move.is_collection_invoice:
                approvals = self.env['payment.approval.record'].search([('invoice_id', '=', move.id)])
                if approvals:
                    approvals.write({
                        'state': 'draft',
                        'invoice_id': False,
                        'approved_by': False,
                        'approved_date': False
                    })
                
                payments = self.env['collection.installment.payment'].search([('invoice_id', '=', move.id)])
                installments = payments.mapped('installment_id')
                
                if payments:
                    payments.unlink()

                if installments:
                    installments._compute_amount_paid()
                    installments._compute_residual()
                    installments._compute_state()