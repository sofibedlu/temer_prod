from odoo import models, fields

class PropertySale(models.Model):
    _inherit = 'property.sale'

    sale_price = fields.Monetary(
        string="Sale Price",
        readonly=False,
        store=True,
        help="The price of the property (Editable)"
    )