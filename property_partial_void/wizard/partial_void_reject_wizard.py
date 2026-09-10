from odoo import models, fields, api, _
from markupsafe import Markup

class PartialVoidRejectWizard(models.TransientModel):
    _name = 'partial.void.reject.wizard'
    _description = 'Reject Partial Void'

    request_id = fields.Many2one('partial.void.request', required=True, readonly=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        req = self.request_id
        req.write({'state': 'rejected'})
        
        msg = Markup(f"<b>Partial Void Request Rejected:</b><br/><b>Reason:</b> {self.reason}")
        
        # Log to all related documents
        req.message_post(body=msg)
        req.collection_id.message_post(body=msg)
        if req.sale_id:
            req.sale_id.message_post(body=msg)