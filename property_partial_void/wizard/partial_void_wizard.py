from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PartialVoidWizard(models.TransientModel):
    _name = 'partial.void.wizard'
    _description = 'Partial Void Request Wizard'

    collection_id = fields.Many2one('collection.order', string="Collection Order", required=True, readonly=True)
    sale_id = fields.Many2one('property.sale', related='collection_id.sale_id', string="Contract")
    parent_property_id = fields.Many2one('property.property', related='sale_id.property_id', string="Merged Property")
    
    reason = fields.Text(string='Reason', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    line_ids = fields.One2many('partial.void.wizard.line', 'wizard_id', string='Units to Drop')

    def action_create_request(self):
        if not self.line_ids:
            raise UserError(_("Please select at least one unit to drop."))

        all_children = self.env['child.property'].search([('parent_property_id', '=', self.parent_property_id.id)])
        if len(self.line_ids) >= len(all_children):
            raise UserError(_("You cannot drop ALL units in a partial void. Please use the standard Full Void workflow instead."))

        request_vals = {
            'collection_id': self.collection_id.id,
            'reason': self.reason,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'line_ids': [(0, 0, {
                'child_property_id': line.child_property_id.id,
                # Store permanent audit snapshots
                'unit_name': line.child_property_id.name,
                'unit_number': line.child_property_id.unit_number,
                'gross_area': line.child_property_id.gross_area,
                'unit_price': line.child_property_id.unit_price,
                'currency_id': line.child_property_id.currency_id.id,
            }) for line in self.line_ids]
        }
        
        new_request = self.env['partial.void.request'].create(request_vals)
        
        if self.attachment_ids:
            self.attachment_ids.sudo().write({
                'res_model': 'partial.void.request',
                'res_id': new_request.id
            })

        msg = Markup(f"<b>Partial Void Requested:</b> A request to drop {len(self.line_ids)} unit(s) has been initiated. Ref: {new_request.name}")
        self.collection_id.message_post(body=msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Request Submitted'),
                'message': _('Partial Void Request %s has been submitted for checking.') % new_request.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

class PartialVoidWizardLine(models.TransientModel):
    _name = 'partial.void.wizard.line'
    _description = 'Partial Void Wizard Line'

    wizard_id = fields.Many2one('partial.void.wizard')
    child_property_id = fields.Many2one('child.property', string="Unit to Drop", required=True)
    gross_area = fields.Float(related='child_property_id.gross_area')
    unit_price = fields.Monetary(related='child_property_id.unit_price')
    currency_id = fields.Many2one('res.currency', related='child_property_id.currency_id')