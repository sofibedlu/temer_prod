from odoo import models, fields

class SettlementRejectWizard(models.TransientModel):
    _name = 'settlement.reject.wizard'
    _description = 'Settlement Request Rejection Wizard'

    request_id = fields.Many2one('early.settlement.request', required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.perform_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}