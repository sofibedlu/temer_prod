from odoo import models, fields

class PropertyProperty(models.Model):
    _inherit = 'property.property'

    is_invalid_duplicate = fields.Boolean(
        string="Invalid Duplicate",
        default=False,
        tracking=True,
        help="Flagged for deletion."
    )