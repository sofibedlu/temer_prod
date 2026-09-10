from odoo import models, fields

class TemerLeadInherit(models.Model):
    _inherit = 'temer.lead'

    is_duplicate_phone = fields.Boolean(
        string='Is Duplicate Phone',
        default=False,
    )