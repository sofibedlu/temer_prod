from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    previous_installment_id = fields.Many2one(
        'collection.installment',
        string='Previous Installment',
        domain="[('collection_id', '=', id)]"
    )
    
    warning_installment_id = fields.Many2one(
        'collection.installment',
        string='Warning Installment',
        domain="[('collection_id', '=', id)]"
    )