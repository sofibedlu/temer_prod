from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    is_property_merged = fields.Boolean(related='property_id.is_merge', string="Is Property Merged")
    
    # Compute if a request is already active
    has_pending_partial_void = fields.Boolean(compute='_compute_has_pending_partial_void')

    def _compute_has_pending_partial_void(self):
        for order in self:
            count = self.env['partial.void.request'].search_count([
                ('collection_id', '=', order.id),
                ('state', 'in', ['draft', 'checked'])
            ])
            order.has_pending_partial_void = count > 0