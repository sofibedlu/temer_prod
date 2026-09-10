from odoo import models, fields

class AmendmentRequestApproveWizard(models.TransientModel):
    _name = 'amendment.request.approve.wizard'
    _description = 'Amendment Request Approve Wizard'

    request_id = fields.Many2one('property.schedule.amendment.request', required=True)
    is_schedule_change = fields.Boolean(related='request_id.is_schedule_change')
    new_partner_name = fields.Char(related='request_id.new_partner_name')

    def action_confirm_approve(self):
        self.ensure_one()
        self.request_id.perform_approval()
        return {'type': 'ir.actions.act_window_close'}