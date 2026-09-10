from odoo import fields, models, _
from odoo.exceptions import UserError


class PropertyPreContractRefundRejectWizard(models.TransientModel):
    _name = 'property.pre.contract.refund.reject.wizard'
    _description = 'Reject Pre Contract Refund'

    refund_id = fields.Many2one(
        'property.pre.contract.refund',
        string='Refund Request',
        required=True,
        ondelete='cascade',
    )
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError(_('Please provide a rejection reason.'))
        self.refund_id.perform_rejection(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}
