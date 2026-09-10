from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    schedule_amendment_request_count = fields.Integer(
        string='Schedule Amendments',
        compute='_compute_schedule_amendment_request_count',
    )
    void_request_count = fields.Integer(
        string='Void Requests',
        compute='_compute_void_request_count',
    )
    refund_request_count = fields.Integer(
        string='Refund Requests',
        compute='_compute_refund_request_count',
    )

    def _request_domain(self):
        self.ensure_one()
        domain = [('collection_id', '=', self.id)]
        if self.sale_id:
            domain = ['|', ('collection_id', '=', self.id), ('sale_id', '=', self.sale_id.id)]
        return domain

    def _refund_request_domain(self):
        self.ensure_one()
        domain = [('void_request_id.collection_id', '=', self.id)]
        if self.sale_id:
            domain = [
                '|',
                ('void_request_id.collection_id', '=', self.id),
                ('void_request_id.sale_id', '=', self.sale_id.id),
            ]
        return domain

    @api.depends('sale_id')
    def _compute_schedule_amendment_request_count(self):
        Request = self.env['property.schedule.amendment.request']
        for order in self:
            order.schedule_amendment_request_count = Request.search_count(order._request_domain())

    @api.depends('sale_id')
    def _compute_void_request_count(self):
        Request = self.env['property.contract.void.request']
        for order in self:
            order.void_request_count = Request.search_count(order._request_domain())

    @api.depends('sale_id')
    def _compute_refund_request_count(self):
        Request = self.env['post.sales.refund.request']
        for order in self:
            order.refund_request_count = Request.search_count(order._refund_request_domain())

    def action_view_schedule_amendment_requests(self):
        self.ensure_one()
        return {
            'name': _('Schedule Amendment Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.schedule.amendment.request',
            'view_mode': 'tree,form',
            'domain': self._request_domain(),
            'context': {'default_collection_id': self.id},
        }

    def action_view_void_requests(self):
        self.ensure_one()
        return {
            'name': _('Void Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.contract.void.request',
            'view_mode': 'tree,form',
            'domain': self._request_domain(),
            'context': {
                'default_collection_id': self.id,
                'default_sale_id': self.sale_id.id,
            },
        }

    def action_view_refund_requests(self):
        self.ensure_one()
        return {
            'name': _('Refund Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'post.sales.refund.request',
            'view_mode': 'tree,form',
            'domain': self._refund_request_domain(),
            'context': {
                'default_collection_id': self.id,
                'default_sale_id': self.sale_id.id,
            },
        }

    def action_open_refund_request_wizard(self):
        self.ensure_one()
        void_request = self.env['property.contract.void.request'].search(
            [('state', '=', 'approved')] + self._request_domain(),
            order='create_date desc, id desc',
            limit=1,
        )
        if not void_request:
            raise UserError(_('No approved void request found for this collection order.'))

        return {
            'name': _('Request Refund'),
            'type': 'ir.actions.act_window',
            'res_model': 'post.sales.refund.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_contract_number': void_request.contract_number or self.contract_number,
                'default_void_request_id': void_request.id,
            },
        }
