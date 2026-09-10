from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    requires_early_reminder = fields.Boolean(
        string="Requires Early Reminder", 
        readonly=True,
        help="Inherited from Property Sale. Indicates installments require early reminders."
    )