from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    commission_payment_id = fields.Many2one(
        "temer.commission.payment",
        string="Commission Payment",
        index=True,
    )