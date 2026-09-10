from odoo import models, fields

class VoidRequestRejectWizard(models.TransientModel):
    _name = 'void.request.reject.wizard'
    _description = 'Void Request Rejection Wizard'

    void_request_id = fields.Many2one('property.contract.void.request', required=True)
    reason = fields.Text(string='Reason for Rejection')

    def action_confirm_reject(self):
        self.ensure_one()
        self.void_request_id.perform_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}