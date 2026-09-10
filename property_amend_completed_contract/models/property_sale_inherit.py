from odoo import models
from markupsafe import Markup

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def action_sync_and_lock_schedule(self):
        # standard Sync logic
        res = super(PropertySale, self).action_sync_and_lock_schedule()
        
        # Update Total Price and Assess the Balance
        for sale in self:
            col_order = sale.collection_order_id
            if col_order:
                col_order.sudo().write({'amount_total': sale.sale_price})

                # If the property price increased, there is now an outstanding balance
                if col_order.amount_remaining > 0:
                    
                    # Reactivate the Collection side
                    if col_order.state == 'completed':
                        col_order.sudo().write({'state': 'active'})
                        col_order.message_post(
                            body=Markup("<b>Collection Reactivated:</b> Sales price amended resulting in a new pending balance. Status reverted from Completed to Active.")
                        )
                    
                    # Reactivate the Contract side
                    if sale.state == 'done':
                        sale.sudo().write({'state': 'approve'})
                        sale.message_post(
                            body=Markup("<b>Contract Reactivated:</b> Sales price amended resulting in a new pending balance. Status reverted from Done to Approved.")
                        )

        return res