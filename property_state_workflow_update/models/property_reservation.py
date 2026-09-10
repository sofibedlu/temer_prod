from odoo import models, api

class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    def write(self, vals):
        # If the blocker is active, strip 'status' from the update values.
        if self.env.context.get('block_sold_transition') and 'status' in vals:
            vals.pop('status')
        return super(PropertyReservation, self).write(vals)