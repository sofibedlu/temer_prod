from odoo import models, api, fields

class PropertyReservationInherited(models.Model):
    _inherit = 'property.reservation'


    @api.model
    def create(self, vals):
        """Create a new reservation with calculated expiration date."""

        expire_date = self.get_expire_date(vals.get('reservation_type_id'))
        # Compute status based on sufficiency if possible
        status = "requested" if self.is_sufficient else "draft"

        vals.update({
            'expire_date': expire_date,
            'status': status
        })
        res = super().create(vals)
        # Mark one-time use if needed
        if res.reservation_type_id.one_time_use:
            res.reservation_type_id.sudo().write({
                'is_used_use': True,
                'used_by_id': self.env.user.id
            })
        # Auto-reserve if quick reservation
        if res.reservation_type_id.reservation_type == 'quick':
            res.approve_reservation()
        return res