from odoo import models, api

class PropertyProperty(models.Model):
    _inherit = 'property.property'

    def write(self, vals):
        # If the blocker is active, strip 'state' from the update values
        if self.env.context.get('block_sold_transition') and 'state' in vals:
            vals.pop('state')
        return super(PropertyProperty, self).write(vals)