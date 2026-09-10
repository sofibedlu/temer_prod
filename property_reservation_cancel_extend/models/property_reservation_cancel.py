from odoo import models, fields, _
from odoo.exceptions import UserError

class PropertyReservationCancelExtend(models.Model):
    _inherit = 'property.reservation'

    # def action_cancel_active_reservations(self):
    #     """
    #     Cancel all active reservations for this property,
    #     and set the property to available.
    #     """
    #     for reservation in self:
    #         property_obj = reservation.property_id
    #         if not property_obj:
    #             continue

    #         # Find all reservations for this property that are not canceled/expired/sold
    #         active_reservations = self.env['property.reservation'].search([
    #             ('property_id', '=', property_obj.id),
    #             ('status', 'in', ['reserved', 'requested', 'pending_sales', 'draft'])
    #         ])
    #         # Cancel each active reservation and set cancellation fields
    #         for active_res in active_reservations:
    #             active_res.write({
    #                 'status': 'canceled',
    #                 'canceled_time': fields.Datetime.now(),
    #                 'canceled_reason': _('Canceled by admin action on reservation with type %s') % (reservation.reservation_type_id.name),
    #             })
    #         # Make the property available
    #         property_obj.sudo().write({'state': 'available'})

    #     return True

    def action_cancel_active_reservation(self):
        """
        Cancel only this reservation and make its property available.
        """
        for reservation in self:
            property_obj = reservation.property_id
            if not property_obj:
                continue

            # Cancel only this reservation
            reservation.write({
                'status': 'canceled',
                'canceled_time': fields.Datetime.now(),
                'canceled_reason': _('Canceled by admin action on reservation with type %s') % (reservation.reservation_type_id.name),
            })
            # Make the property available
        if not property_obj.state in ['draft','sold','pending_sales']:
            property_obj.sudo().write({'state': 'available'})

        return True
    

