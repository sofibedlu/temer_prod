# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

SOLD_PROPERTY_STATES = ('sold', 'pending_sales')
ACTIVE_RESERVATION_STATUSES = ('reserved', 'requested', 'pending_sales', 'draft')


class PropertyPropertyStateChange(models.Model):
    _inherit = 'property.property'

    def _raise_if_sold(self):
        sold_records = self.filtered(lambda rec: rec.state in SOLD_PROPERTY_STATES)
        if sold_records:
            raise UserError(_("It's already sold."))

    def _open_state_change_confirm_wizard(self, target_state):
        return {
            'name': _('Confirm'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.state.change.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_property_ids': [(6, 0, self.ids)],
                'default_target_state': target_state,
            },
        }

    def _cancel_active_reservations(self, target_state_label):
        Reservation = self.env['property.reservation']
        now = fields.Datetime.now()
        user_name = self.env.user.name
        follow_up_stage = self.env['crm.stage'].search([('name', 'ilike', 'Follow Up')], limit=1)
        for prop in self:
            reservations = Reservation.search([
                ('property_id', '=', prop.id),
                ('status', 'in', list(ACTIVE_RESERVATION_STATUSES)),
            ])
            for reservation in reservations:
                reservation.write({
                    'status': 'canceled',
                    'canceled_time': now,
                    'canceled_reason': _(
                        'Canceled because property was set to %(state)s by %(user)s'
                    ) % {'state': target_state_label, 'user': user_name},
                })
                if follow_up_stage and reservation.crm_lead_id:
                    reservation.crm_lead_id.write({'stage_id': follow_up_stage.id})

    def _log_reservation_cancel_note(self, before_states, reserved_before):
        for rec in self:
            if not reserved_before.get(rec.id):
                continue
            old_state = before_states.get(rec.id)
            if old_state == rec.state:
                continue
            state_label = dict(self._fields['state'].selection).get(rec.state, rec.state)
            body = _(
                'Reservation canceled and property set to %(state)s by %(user)s.'
            ) % {'state': state_label, 'user': self.env.user.name}
            if hasattr(rec, '_log_property_chatter'):
                rec._log_property_chatter(body=body)
            else:
                rec.message_post(
                    body=body,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    def action_available(self):
        self._raise_if_sold()
        if (
            self.filtered(lambda rec: rec.state == 'reserved')
            and not self.env.context.get('confirm_property_state_change')
        ):
            return self._open_state_change_confirm_wizard('available')

        before_states = {rec.id: rec.state for rec in self}
        reserved_before = {rec.id: rec.state == 'reserved' for rec in self}
        reserved_records = self.filtered(lambda rec: reserved_before[rec.id])
        if reserved_records:
            reserved_records._cancel_active_reservations(_('Available'))

        res = super().action_available()
        self._log_reservation_cancel_note(before_states, reserved_before)
        return res

    def action_draft(self):
        self._raise_if_sold()
        if (
            self.filtered(lambda rec: rec.state == 'reserved')
            and not self.env.context.get('confirm_property_state_change')
        ):
            return self._open_state_change_confirm_wizard('draft')

        before_states = {rec.id: rec.state for rec in self}
        reserved_before = {rec.id: rec.state == 'reserved' for rec in self}
        reserved_records = self.filtered(lambda rec: reserved_before[rec.id])
        if reserved_records:
            reserved_records._cancel_active_reservations(_('Draft'))

        res = super().action_draft()
        self._log_reservation_cancel_note(before_states, reserved_before)
        return res
