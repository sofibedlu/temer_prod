from odoo import models, fields

class PropertyPaymentTermLine(models.Model):
    _inherit = 'property.payment.term.line'

    is_standard = fields.Boolean(
        string="Standard",
        default=False
    )