from odoo import models, api
from odoo.tools import float_compare

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def _create_collection_order(self):
        """
        to wipe out due dates on fully paid installments,
        """
        collection = super(PropertySale, self.with_context(collection_creation_bypass=True))._create_collection_order()

        # Post-Creation Cleanup
        for installment in collection.installment_ids:
            
            is_paid = installment.state == 'paid' or (
                installment.amount_total > 0 and 
                float_compare(installment.amount_paid, installment.amount_total, precision_digits=2) >= 0
            )
            
            if is_paid and installment.due_date:
                
                self.env.cr.execute("""
                    UPDATE collection_installment 
                    SET due_date = NULL 
                    WHERE id = %s
                """, (installment.id,))

        collection.installment_ids.invalidate_recordset(['due_date'])
                
        return collection