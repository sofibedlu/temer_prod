from odoo import models

class ProcurementRequest(models.Model):
    _inherit = 'procurement.request'

    def _check_if_fully_ordered(self):
        """ Checks if all requested quantities have confirmed POs """
        self.ensure_one()

        po_lines = self.env['purchase.order.line'].search([
            ('order_id.custom_evaluation_id.procurement_ids', 'in', self.id),
            ('order_id.state', 'in', ['purchase', 'done'])
        ])
        
        ordered_qty_by_product = {}
        for pol in po_lines:
            ordered_qty_by_product[pol.product_id.id] = ordered_qty_by_product.get(pol.product_id.id, 0) + pol.product_qty

        for line in self.line_ids:
            if ordered_qty_by_product.get(line.product_id.id, 0) < line.quantity:
                return False 
        return True