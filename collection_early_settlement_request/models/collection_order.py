from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    early_settlement_history_ids = fields.One2many(
         'early.settlement.history', 
         'collection_id', 
         string='Early Settled Installments',
         domain=[('request_id.state', '=', 'approved')],
         readonly=True
     )