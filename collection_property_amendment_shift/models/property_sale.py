from odoo import models, fields

class PropertySale(models.Model):
    _inherit = 'property.sale'

    is_site_shifted = fields.Boolean(
        string="Site Shifted", 
        readonly=True, 
        tracking=True, 
        help="Customer was migrated from a different site via Amendment."
    )