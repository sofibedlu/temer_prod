from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_void_refund = fields.Boolean(string="Is Void Refund", default=False)
    void_penalty_amount = fields.Monetary(string="Void Penalty Deducted", currency_field='currency_id')