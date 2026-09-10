from odoo import models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
  
        res = super().button_confirm()
        
        # Check if we need to revert the Request back to 'approved'
        for po in self:
            if po.custom_evaluation_id:
                for req in po.custom_evaluation_id.procurement_ids:
                    if not req._check_if_fully_ordered():
                        req.sudo().write({'state': 'approved'})
                        
        return res