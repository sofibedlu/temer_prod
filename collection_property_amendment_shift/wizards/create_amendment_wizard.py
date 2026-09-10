from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PropertyAmendmentCreateWizard(models.TransientModel):
    _inherit = 'property.amendment.create.wizard'

    is_site_shift = fields.Boolean(string="Transfer to a Different Site?", default=False)
    new_site_id = fields.Many2one('property.site', string="New Target Site")

    @api.onchange('is_site_shift')
    def _onchange_is_site_shift(self):
        self.new_site_id = False
        self.new_property_id = False

    @api.onchange('new_site_id')
    def _onchange_new_site_id(self):
        if self.new_property_id and self.is_site_shift and self.new_property_id.site != self.new_site_id:
            self.new_property_id = False

    def action_create_request(self):
        if self.is_site_shift:
            if not self.new_site_id:
                raise UserError(_("Please select a new target site for the shift."))
            if self.new_site_id.id == self.site_id.id:
                raise UserError(_("The new target site must be different from the current site."))

        # Determine final site
        target_site_id = self.new_site_id.id if self.is_site_shift else self.site_id.id

        request_vals = {
            'collection_order_id': self.collection_order_id.id,
            'old_property_id': self.old_property_id.id,
            'new_site_id': target_site_id,
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
        
        shift_text = f"<br/><b>Site Shift:</b> {self.site_id.name} &rarr; {self.new_site_id.name}" if self.is_site_shift else ""
        
        msg = f"<b>Property Amendment Requested ({new_request.name})</b>{shift_text}<br/>" \
              f"<b>Target New Property:</b> {self.new_property_id.name}<br/>" \
              f"<b>Reason:</b> {self.reason}"
        self.collection_order_id.sudo().message_post(body=Markup(msg))
        
        return {'type': 'ir.actions.act_window_close'}