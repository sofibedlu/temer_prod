from odoo import models, fields
from markupsafe import Markup

class PropertyAmendmentCreateWizard(models.TransientModel):
    _name = 'property.amendment.create.wizard'
    _description = 'Create Property Amendment Request Wizard'

    collection_order_id = fields.Many2one('collection.order', string="Collection Order", required=True)
    old_property_id = fields.Many2one('property.property', string="Current Property", readonly=True)
    site_id = fields.Many2one('property.site', related='old_property_id.site', string="Site")
    
    new_property_id = fields.Many2one(
        'property.property', 
        string="New Property", 
        required=True,
        domain="[('site', '=', site_id), ('state', '=', 'available')]"
    )
    reason = fields.Text(string="Reason for Amendment", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

    def action_create_request(self):
        request_vals = {
            'collection_order_id': self.collection_order_id.id,
            'old_property_id': self.old_property_id.id,
            'new_property_id': self.new_property_id.id,
            'reason': self.reason,
            'state': 'submitted',
            'attachment_ids': [(6, 0, self.attachment_ids.ids)] if self.attachment_ids else False
        }
        new_request = self.env['property.amendment.request'].sudo().create(request_vals)

        if self.attachment_ids:
            self.attachment_ids.sudo().write({
                'res_model': 'property.amendment.request',
                'res_id': new_request.id
            })
        
        msg = f"<b>Property Amendment Requested ({new_request.name})</b><br/>" \
              f"<b>Target New Property:</b> {self.new_property_id.name}<br/>" \
              f"<b>Reason:</b> {self.reason}"
        self.collection_order_id.sudo().message_post(body=Markup(msg))
        
        return {'type': 'ir.actions.act_window_close'}