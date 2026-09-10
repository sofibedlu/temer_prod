from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    amendment_request_ids = fields.One2many('property.amendment.request', 'collection_order_id', string="Amendment Requests")
    property_amendment_count = fields.Integer(compute='_compute_property_amendment_count', string="Property Amendments")
    has_pending_property_amendment = fields.Boolean(compute='_compute_has_pending_property_amendment')

    @api.depends('amendment_request_ids.state')
    def _compute_has_pending_property_amendment(self):
        for order in self:
            pending = order.amendment_request_ids.filtered(lambda r: r.state in ['submitted', 'checked'])
            order.has_pending_property_amendment = bool(pending)

    @api.depends('amendment_request_ids')
    def _compute_property_amendment_count(self):
        for order in self:
            order.property_amendment_count = len(order.amendment_request_ids)

    def action_view_property_amendments(self):
        self.ensure_one()
        return {
            'name': 'Property Amendments',
            'type': 'ir.actions.act_window',
            'res_model': 'property.amendment.request',
            'view_mode': 'tree,form',
            'domain': [('collection_order_id', '=', self.id)],
            'context': {'default_collection_order_id': self.id},
        }

    def action_open_property_amendment_wizard(self):
        return {
            'name': 'Request Property Amendment',
            'type': 'ir.actions.act_window',
            'res_model': 'property.amendment.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_order_id': self.id,
                'default_old_property_id': self.property_id.id if hasattr(self, 'property_id') else False, 
            }
        }