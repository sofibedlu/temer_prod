from odoo import models, fields

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    is_advance_remaining = fields.Boolean(
        string="Is Advance Remaining", 
        default=False,
        help="Check this if this installment is part of a deferred full-payment/downpayment."
    )