from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    collection_site_ids = fields.Many2many(
        'property.site', 
        'collection_user_site_rel',
        'user_id', 
        'site', 
        string='Allowed Collection Sites',
        help="The sites this user is allowed to manage collections for."
    )