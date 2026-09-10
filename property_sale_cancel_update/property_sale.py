from odoo import models

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def write(self, vals):
        res = super(PropertySale, self).write(vals)
        if vals.get('state') == 'cancel':
            for sale in self:
                if hasattr(sale, 'contract_id') and sale.contract_id:
                    for contract in sale.contract_id.sudo():
                        old_name = contract.name
                        if old_name and not old_name.endswith('-canceled'):
                            base_canceled_name = f"{old_name}-canceled"
                            new_name = base_canceled_name
                            counter = 1
                            
                            while self.env['contract.application'].sudo().search_count([('name', '=', new_name)]):
                                new_name = f"{base_canceled_name}-{counter}"
                                counter += 1
                                
                            contract.sudo().write({'name': new_name})
        return res