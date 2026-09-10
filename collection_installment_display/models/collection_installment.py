from odoo import models, fields

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    payment_term_name = fields.Char(
        string='Term / Milestone Name',
        related='payment_term_line_id.name',
        readonly=True,
        help="The live, dynamic name from the payment term configuration."
    )