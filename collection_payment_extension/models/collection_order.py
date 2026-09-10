from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    extension_request_ids = fields.One2many('collection.payment.extension.request', 'collection_id')
    extension_request_count = fields.Integer(compute='_compute_extension_request_count')
    has_pending_extension = fields.Boolean(
        compute='_compute_has_pending_extension', 
        string='Has Pending Extension'
    )

    @api.depends('extension_request_ids')
    def _compute_extension_request_count(self):
        for rec in self:
            rec.extension_request_count = len(rec.extension_request_ids)

    @api.depends('extension_request_ids.state')
    def _compute_has_pending_extension(self):
        for rec in self:
            rec.has_pending_extension = any(
                req.state in ('pending') for req in rec.extension_request_ids
            )

    def action_view_extension_requests(self):
        self.ensure_one()
        return {
            'name': 'Extension Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'collection.payment.extension.request',
            'view_mode': 'tree,form',
            'domain': [('collection_id', '=', self.id)],
            'context': {'default_collection_id': self.id}
        }