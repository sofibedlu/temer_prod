from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    is_site_shifted = fields.Boolean(
        string="Site Shifted", 
        readonly=True, 
        tracking=True, 
        help="Customer was migrated from a different site via Amendment."
    )