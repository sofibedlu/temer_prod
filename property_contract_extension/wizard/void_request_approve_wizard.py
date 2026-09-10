from odoo import models, fields

class VoidRequestApproveWizard(models.TransientModel):
    _name = 'void.request.approve.wizard'
    _description = 'Void Request Approve Wizard'

    request_id = fields.Many2one('property.contract.void.request', required=True)

    def action_confirm_approve(self):
        self.ensure_one()
        self.request_id.perform_approval()
        return {'type': 'ir.actions.act_window_close'}