from odoo import models

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def _create_collection_order(self):
        return super(PropertySale, self.sudo())._create_collection_order()