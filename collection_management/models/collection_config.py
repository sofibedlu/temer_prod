from odoo import models, fields, api

class CollectionDiscountConfig(models.Model):
    _name = 'collection.discount.config'
    _description = 'Discount Limits Configuration'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Description', required=True, default='Discount Config')
    active = fields.Boolean(default=True)
    max_manual_discount_percentage = fields.Float(string="Max Manual Discount %", default=3.0, help="Max % for manual discounts during payment.")
    max_early_settlement_percentage = fields.Float(string="Max Early Settlement %", default=10.0, help="Max % for early settlement wizard.")