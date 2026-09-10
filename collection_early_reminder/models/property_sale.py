from odoo import models, fields

class PropertySale(models.Model):
    _inherit = 'property.sale'

    requires_early_reminder = fields.Boolean(
        string="Requires Early Reminder", 
        default=False,
        help="Check this if the customer must receive payment request letters 1 month prior to their due dates."
    )

    def _create_collection_order(self):
        collection = super(PropertySale, self)._create_collection_order()

        if self.requires_early_reminder:
            collection.write({'requires_early_reminder': True})

        return collection