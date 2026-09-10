from odoo import _, fields, models
from odoo.exceptions import ValidationError


class CancelReservationRequestWizard(models.TransientModel):
    _name = 'cancel.reservation.request.wizard'
    _description = 'Cancel Reservation Request Wizard'

    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        required=True,
        readonly=True,
    )
    reason_id = fields.Many2one(
        'property.sale.cancel.reason',
        string='Reason',
    )
    other = fields.Boolean(default=False)
    reason = fields.Text(string='Other Reason')

    def action_create_request(self):
        self.ensure_one()
        reservation = self.reservation_id
        if reservation.reservation_type_id.reservation_type == 'quick':
            raise ValidationError(_('Quick reservations must use the direct cancel button.'))
        if not reservation.cancel_request_can_request:
            raise ValidationError(_('You are not allowed to request cancellation for this reservation.'))
        if reservation.status not in ['requested', 'reserved']:
            raise ValidationError(_('Only requested or reserved reservations can be canceled by request.'))
        if self.other and not self.reason:
            raise ValidationError(_('Please enter the other cancellation reason.'))
        if not self.other and not self.reason_id:
            raise ValidationError(_('Please select a cancellation reason.'))

        self.env['property.reservation.cancel.request'].sudo().create({
            'reservation_id': reservation.id,
            'requested_by_id': self.env.user.id,
            'reason_id': self.reason_id.id,
            'other': self.other,
            'reason': self.reason,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
