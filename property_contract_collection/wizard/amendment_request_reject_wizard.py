from odoo import models, fields

class AmendmentRequestRejectWizard(models.TransientModel):
    _name = 'amendment.request.reject.wizard'
    _description = 'Amendment Request Rejection Wizard'

    request_id = fields.Many2one('property.schedule.amendment.request', required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.perform_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}