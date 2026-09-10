from odoo import models, fields, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    approval_date = fields.Date(string="Approval Date", readonly=True, copy=False, tracking=True)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     return super(PropertySale, self.with_context(block_sold_transition=True)).create(vals_list)

    def action_confirm(self):
        # Pass context blocker to prevent state updates on Property/Reservation during Confirmation
        return super(PropertySale, self.with_context(block_sold_transition=True)).action_confirm()

    def action_approve_sale(self):
        res = super(PropertySale, self).action_approve_sale()
        
        for sale in self:
            sale.approval_date = fields.Date.context_today(sale)
            
            if sale.property_id and sale.property_id.state != 'sold':
                sale.property_id.sudo().write({'state': 'sold'})
                
            if sale.reservation_id:
                sale.reservation_id.sudo().write({'status': 'sold'})
                
        return res