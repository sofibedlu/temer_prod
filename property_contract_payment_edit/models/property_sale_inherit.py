from odoo import models

class PropertySale(models.Model):
    _inherit = 'property.sale'

    def add_payment_list(self):
        """ Inject context flag into the wizard action """
        action = super(PropertySale, self).add_payment_list()
        
        if isinstance(action, dict):
            ctx = action.get('context', {})
            if not isinstance(ctx, dict):
                ctx = {}
            ctx['from_sales_wizard'] = True
            action['context'] = ctx
            
        return action