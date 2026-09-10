from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_technical_approve(self):
        self.ensure_one()
        return {
            'name': 'Technical Verification',
            'type': 'ir.actions.act_window',
            'res_model': 'picking.technical.verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }