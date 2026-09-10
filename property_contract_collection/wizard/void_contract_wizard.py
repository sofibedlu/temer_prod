from odoo import models, fields, _
from markupsafe import Markup

class VoidContractWizard(models.TransientModel):
    _inherit = 'void.contract.wizard'

    collection_id = fields.Many2one('collection.order', string='Collection Order', readonly=True)

    def action_submit_request(self):
        self.ensure_one()
        target_sale_id = self.sale_id.id
        if not target_sale_id and self.collection_id:
            target_sale_id = self.collection_id.sale_id.id

        request = self.env['property.contract.void.request'].sudo().create({
            'collection_id': self.collection_id.id if self.collection_id else False,
            'sale_id': target_sale_id,
            'reason': self.reason,
        })

        if self.collection_id:
            self.collection_id.sudo().message_post(
                body=Markup("<b>Void Request Created</b><br/>"
                            "Reference: %s<br/>"
                            "Reason: %s") % (request.name, self.reason),
            )
            
        return {'type': 'ir.actions.act_window_close'}