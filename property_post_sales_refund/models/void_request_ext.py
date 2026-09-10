from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyContractVoidRequest(models.Model):
    _inherit = 'property.contract.void.request'

    site_name = fields.Char(related='property_id.site.name', string='Site Name', readonly=True)
    property_type_name = fields.Selection(related='property_id.property_type', string='Property Type', readonly=True)
    floor_number = fields.Many2one(related='property_id.floor_id', string='Floor Number', readonly=True)
    house_number = fields.Char(related='property_id.unit_number', string='House Number', readonly=True)
    buyer_name = fields.Html(string='Buyer Names', compute='_compute_buyer_name', readonly=True)
    refund_count = fields.Integer(compute='_compute_refund_count', string="Refund Count")

    @api.depends('collection_id.buyers_name', 'sale_id.collection_order_id.buyers_name')
    def _compute_buyer_name(self):
        for req in self:
            order = req.collection_id or (req.sale_id.collection_order_id if req.sale_id else False)
            req.buyer_name = order.buyers_name if order else False

    def _compute_refund_count(self):
        refund_model = self.env['post.sales.refund.request']
        for rec in self:
            rec.refund_count = refund_model.search_count([('void_request_id', '=', rec.id)])

    def action_view_refunds(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Refund Requests',
            'res_model': 'post.sales.refund.request',
            'view_mode': 'tree,form',
            'domain': [('void_request_id', '=', self.id)],
        }
    
    def action_check(self):
        """ remove the pay_date validation """
        for record in self:
            if record.penalty_percent < 0 or record.penalty_percent > 100:
                raise UserError(_("Penalty percentage must be between 0 and 100."))
                
            if record.state == 'draft':
                record.state = 'checked'