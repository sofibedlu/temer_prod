from odoo import models, fields

class CollectionSiteAccess(models.Model):
    _inherit = 'collection.site.access'

    supervisor_id = fields.Many2one(
        'res.users', 
        string="Supervisor", 
        help="The supervisor overseeing this collection officer for these sites."
    )