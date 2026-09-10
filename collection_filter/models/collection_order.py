# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    property_name = fields.Char(
        string='Property Name',
        related='property_id.name',
        store=True,
        readonly=True,
        index=True
    )
    
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        related='property_id.site',
        store=True,
        readonly=True
    )
    
    site_name = fields.Char(
        string='Site Name',
        related='site_id.name',
        store=True,
        readonly=True,
        index=True
    )
    
    customer_name = fields.Char(
        string='Customer Name',
        related='partner_id.name',
        store=True,
        readonly=True,
        index=True
    )
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Override to search across collection reference, customer name, property name, and site name"""
        args = args or []
        domain = []
        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('customer_name', operator, name)],
                [('property_name', operator, name)],
                [('site_name', operator, name)],
            ])
        return super(CollectionOrder, self)._name_search(name, args + domain, operator=operator, limit=limit, order=order)

