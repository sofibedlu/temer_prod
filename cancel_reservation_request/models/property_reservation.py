from odoo import _, fields, models
from odoo.exceptions import ValidationError


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    cancel_request_is_quick_reservation = fields.Boolean(
        compute='_compute_cancel_request_is_quick_reservation'
    )
    cancel_request_can_request = fields.Boolean(
        compute='_compute_cancel_request_can_request'
    )
    cancel_request_ids = fields.One2many(
        'property.reservation.cancel.request',
        'reservation_id',
        string='Cancel Requests',
        readonly=True,
    )
    latest_cancel_request_id = fields.Many2one(
        'property.reservation.cancel.request',
        string='Latest Cancel Request',
        compute='_compute_latest_cancel_request',
    )
    has_cancel_request = fields.Boolean(
        string='Has Cancel Request',
        compute='_compute_latest_cancel_request',
    )
    cancel_request_state = fields.Selection(
        [
            ('prepare', 'Prepare'),
            ('check', 'Check'),
            ('approve', 'Approve'),
        ],
        string='Cancellation',
        compute='_compute_latest_cancel_request',
    )
    cancel_request_reason = fields.Text(
        string='Cancellation Reason',
        compute='_compute_latest_cancel_request',
    )

    def _compute_cancel_request_is_quick_reservation(self):
        for reservation in self:
            reservation.cancel_request_is_quick_reservation = (
                reservation.reservation_type_id.reservation_type == 'quick'
            )

    def _compute_cancel_request_can_request(self):
        can_request_by_group = (
            self.env.user.has_group('temer_structure.access_property_sales_supervisor_group')
            or self.env.user.has_group('temer_structure.access_property_sales_team_manager_group')
            or self.env.user.has_group('temer_structure.access_property_wing_manager_group')
            or self.env.user.has_group('temer_structure.access_property_reservation_manager_group')
        )
        for reservation in self:
            reservation.cancel_request_can_request = (
                can_request_by_group or reservation.salesperson_ids == self.env.user
            )

    def _compute_latest_cancel_request(self):
        for reservation in self:
            latest_request = self.env['property.reservation.cancel.request'].sudo().search(
                [('reservation_id', '=', reservation.id)],
                order='create_date desc',
                limit=1,
            )
            reservation.latest_cancel_request_id = latest_request
            reservation.has_cancel_request = bool(latest_request)
            reservation.cancel_request_state = latest_request.state if latest_request else False
            reservation.cancel_request_reason = latest_request.cancel_reason if latest_request else False

    def action_open_cancel_request_wizard(self):
        self.ensure_one()
        if self.reservation_type_id.reservation_type == 'quick':
            raise ValidationError(_('Quick reservations must use the direct cancel button.'))
        if not self.cancel_request_can_request:
            raise ValidationError(_('You are not allowed to request cancellation for this reservation.'))
        if self.status not in ['requested', 'reserved']:
            raise ValidationError(_('Only requested or reserved reservations can be canceled by request.'))

        pending_request = self.env['property.reservation.cancel.request'].sudo().search([
            ('reservation_id', '=', self.id),
            ('state', 'in', ['prepare', 'check']),
        ], limit=1)
        if pending_request:
            raise ValidationError(_('A cancel request already exists for this reservation.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Reservation Request'),
            'res_model': 'cancel.reservation.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
            },
        }


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    latest_active_reservation_id = fields.Many2one(
        'property.reservation',
        compute='_compute_latest_active_reservation',
    )
    latest_active_reservation_is_quick = fields.Boolean(
        compute='_compute_latest_active_reservation',
    )
    latest_active_reservation_is_requestable = fields.Boolean(
        compute='_compute_latest_active_reservation',
    )

    def _compute_latest_active_reservation(self):
        Reservation = self.env['property.reservation'].sudo()
        for property_rec in self:
            reservation = Reservation.search([
                ('property_id', '=', property_rec.id),
                ('status', 'in', ['draft', 'requested', 'reserved']),
            ], order='create_date desc, id desc', limit=1)
            property_rec.latest_active_reservation_id = reservation
            property_rec.latest_active_reservation_is_quick = (
                reservation.reservation_type_id.reservation_type == 'quick'
            )
            property_rec.latest_active_reservation_is_requestable = bool(
                reservation and reservation.reservation_type_id.reservation_type != 'quick'
            )

    def cancel_reservation(self):
        self.ensure_one()
        reservation = self.env['property.reservation'].search([
            ('property_id', '=', self.id),
            ('status', 'in', ['draft', 'requested', 'reserved']),
        ], order='create_date desc, id desc', limit=1)

        if not reservation:
            return super().cancel_reservation()

        if reservation.reservation_type_id.reservation_type == 'quick':
            return reservation.cancel_reservation()

        return reservation.action_open_cancel_request_wizard()
