from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'
    
    discount_request_ids = fields.One2many('discount.request', 'collection_id', string='Discount Requests')
    discount_request_count = fields.Integer(compute='_compute_discount_request_count', string='Discount Requests')
    has_pending_discount_request = fields.Boolean(
        string='Has Pending Discount Request', 
        compute='_compute_has_pending_discount_request'
    )

    @api.depends('discount_request_ids.state')
    def _compute_has_pending_discount_request(self):
        for rec in self:
            rec.has_pending_discount_request = any(
                req.state in ('pending') for req in rec.discount_request_ids
            )

    @api.depends('discount_request_ids')
    def _compute_discount_request_count(self):
        for rec in self:
            rec.discount_request_count = len(rec.discount_request_ids)

    def action_view_discount_requests(self):
        self.ensure_one()
        return {
            'name': 'Discount Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'discount.request',
            'view_mode': 'tree,form',
            'domain': [('collection_id', '=', self.id)],
            'context': {'default_collection_id': self.id}
        }

    def action_open_discount_request_wizard(self):
        self.ensure_one()
        return {
            'name': 'Request Discount',
            'type': 'ir.actions.act_window',
            'res_model': 'discount.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }