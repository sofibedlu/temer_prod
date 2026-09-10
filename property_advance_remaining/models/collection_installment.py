from odoo import models, fields

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    is_advance_remaining = fields.Boolean(
        string="Advance Remaining", 
        default=False, 
        readonly=True,
        help="Indicates if this is a deferred advance payment."
    )