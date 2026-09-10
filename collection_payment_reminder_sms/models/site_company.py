from odoo import models, fields

class SiteCompany(models.Model):
    _inherit = 'site.company'

    name_amharic = fields.Char(
        string="Company Name (Amharic)",
        help="Amharic translation of the company name."
    )