from odoo import models, fields

class DiscountRequestRejectWizard(models.TransientModel):
    _name = 'discount.request.reject.wizard'
    _description = 'Discount Request Rejection Wizard'

    request_id = fields.Many2one('discount.request', required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.perform_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}