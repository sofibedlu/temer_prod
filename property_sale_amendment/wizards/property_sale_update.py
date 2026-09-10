from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertySaleUpdateWizard(models.TransientModel):
    _name = 'property.sale.update.wizard'
    _description = 'Update Confirmed Sale'

    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True)
    partner_id = fields.Many2one('res.partner', string='New Customer')
    contract_number = fields.Char(string='New Contract Number')
    property_id = fields.Many2one('property.property', string='New Property')
    payment_term_id = fields.Many2one('property.payment.term', string='Payment Term')
    
    @api.model
    def default_get(self, fields):
        res = super(PropertySaleUpdateWizard, self).default_get(fields)
        if self._context.get('active_id'):
            sale = self.env['property.sale'].browse(self._context.get('active_id'))
            res.update({
                'sale_id': sale.id,
                'partner_id': sale.partner_id.id,
                'property_id': sale.property_id.id,
                'contract_number': sale.contract_number,
                'payment_term_id': sale.property_payment_term.id,
            })
        return res

    @api.onchange('property_id')
    def _onchange_property_id(self):
        """Auto-select the correct payment term when property changes."""
        if self.property_id:
            if self.property_id.site_payment_structure_id:
                 self.payment_term_id = self.property_id.site_payment_structure_id.payment_term_id.id
            elif self.property_id.payment_structure_id:
                self.payment_term_id = self.property_id.payment_structure_id.id
            elif self.property_id.site.payment_structure_id:
                self.payment_term_id = self.property_id.site.payment_structure_id.id

    def action_apply_changes(self):
        self.ensure_one()
        sale = self.sale_id

        vals = {}
        if self.partner_id:
            vals['partner_id'] = self.partner_id.id

        if self.property_id:
            vals['property_id'] = self.property_id.id
            # Update Sale Price from the new Property's unit price
            vals['sale_price'] = self.property_id.unit_price
        
        # Payment Term
        if self.payment_term_id:
            vals['property_payment_term'] = self.payment_term_id.id

        if vals:
            sale.sudo().write(vals)

        if self.contract_number and sale.contract_id:
            sale.contract_id[0].sudo().write({'name': self.contract_number})

        # Regenerate Installment Lines
        if 'sale_price' in vals or 'property_payment_term' in vals:
            sale.recalculate_payment_line_based_on_payment_term()
        
        return {'type': 'ir.actions.act_window_close'}