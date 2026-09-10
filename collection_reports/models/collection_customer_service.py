from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CollectionCustomerService(models.Model):
    _name = 'collection.customer.service'
    _description = 'Collection Customer Service Feedback'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, default=lambda self: 'New', readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    
    # Make collection_id optional to avoid dependency issues during model registration
    collection_id = fields.Many2one(
        'collection.order', 
        string='Collection Order', 
        required=False, 
        ondelete='set null',
        help='Collection Order (optional)'
    )
    total_customers = fields.Integer(string='Total Number of Customers Obtained Service', default=1)
    satisfaction_level = fields.Selection([
        ('very_satisfied', 'Very Satisfied'),
        ('satisfied', 'Satisfied'),
        ('neutral', 'Neutral'),
        ('dissatisfied', 'Dissatisfied'),
        ('very_dissatisfied', 'Very Dissatisfied'),
    ], string='Satisfaction Level', required=True)
    remark = fields.Text(string='Remark')
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    create_date = fields.Datetime(string='Created On', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('collection.customer.service') or 'New'
        return super(CollectionCustomerService, self).create(vals)
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get to add dynamic domain for partner_id"""
        res = super(CollectionCustomerService, self).fields_get(allfields, attributes)
        if 'partner_id' in res:
            # Get customers who have collection orders
            collection_orders = self.env['collection.order'].search([])
            partner_ids = collection_orders.mapped('partner_id').ids
            if partner_ids:
                res['partner_id']['domain'] = [('id', 'in', partner_ids)]
            else:
                res['partner_id']['domain'] = [('id', 'in', [])]
        return res
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Filter collection orders by selected customer and clear collection_id if customer changes"""
        if self.partner_id:
            # Clear collection_id if it doesn't belong to the selected customer
            if self.collection_id and self.collection_id.partner_id != self.partner_id:
                self.collection_id = False
            return {
                'domain': {'collection_id': [('partner_id', '=', self.partner_id.id)]}
            }
        else:
            self.collection_id = False
            return {
                'domain': {'collection_id': []}
            }

