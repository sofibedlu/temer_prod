from odoo import models, fields, api, _
from markupsafe import Markup

class PropertyContractVoidRequest(models.Model):
    _inherit = 'property.contract.void.request'

    collection_id = fields.Many2one('collection.order', string='Collection Order', readonly=True)

    def action_view_collection(self):
        self.ensure_one()
        if not self.collection_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Collection Order'),
            'res_model': 'collection.order',
            'res_id': self.collection_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def perform_rejection(self, reason):
        for req in self:
            req.write({'state': 'rejected', 'rejection_reason': reason})
            if req.collection_id:
                req.collection_id.sudo().message_post(
                    body=Markup(
                        "<b>Void Request Rejected</b><br/>Request Ref: %s<br/>Reason: %s<br/>The contract remains active."
                    ) % (req.name, reason)
                )
            elif req.sale_id:
                req.sale_id.sudo().message_post(
                    body=Markup(
                        "<b>Void Request Rejected</b><br/>Request Ref: %s<br/>Reason: %s<br/>The contract remains active."
                    ) % (req.name, reason)
                )