from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    total_discount = fields.Monetary(
        string='Pre-Discount', 
        currency_field='currency_id',
        help="Total discount applied at the property sale (contract) level."
    )