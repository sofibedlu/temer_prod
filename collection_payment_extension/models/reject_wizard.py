from odoo import models, fields

class ExtensionRequestRejectWizard(models.TransientModel):
    _name = 'extension.request.reject.wizard'
    _description = 'Extension Request Rejection Wizard'

    request_id = fields.Many2one('collection.payment.extension.request', required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.perform_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}