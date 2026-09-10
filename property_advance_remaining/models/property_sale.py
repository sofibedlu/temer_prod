from odoo import models, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def _create_collection_order(self):
        collection = super(PropertySale, self)._create_collection_order()

        for sale_line in self.payment_installment_line_ids:
            if sale_line.is_advance_remaining:
                coll_line = collection.installment_ids.filtered(
                    lambda l: l.payment_term_line_id.id == sale_line.payment_term_id.id 
                              and l.sequence == sale_line.sequence
                )
                if coll_line:
                    coll_line.write({'is_advance_remaining': True})

        return collection