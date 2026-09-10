from odoo import models, fields
from markupsafe import Markup

class PropertyAmendmentRejectWizard(models.TransientModel):
    _name = 'property.amendment.reject.wizard'
    _description = 'Reject Property Amendment Request'

    amendment_request_id = fields.Many2one('property.amendment.request', required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_reject(self):
        req = self.amendment_request_id
        req.write({
            'state': 'rejected',
            'rejection_reason': self.reason
        })
        
        if req.collection_order_id:
            msg = f"<b>Property Amendment Rejected ({req.name})</b><br/>" \
                  f"<b>Rejection Reason:</b> {self.reason}"
            req.collection_order_id.sudo().message_post(body=Markup(msg))
            
        return {'type': 'ir.actions.act_window_close'}