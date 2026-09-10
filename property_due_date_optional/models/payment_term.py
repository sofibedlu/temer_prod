from odoo import models, fields

class PropertyPaymentTermLine(models.Model):
    _inherit = 'property.payment.term.line'

    date_optional = fields.Boolean(
        string="Date Optional", 
        default=False,
        help="If checked, this milestone will not require a due date even in Time-Based schedules."
    )