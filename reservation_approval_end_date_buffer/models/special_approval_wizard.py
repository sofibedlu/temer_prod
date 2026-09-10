# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.special_reservation_manager_step.models.special_approval_wizard import (
        SpecialApprovalWizardManagerStep,
    )
except ImportError:
    SpecialApprovalWizardManagerStep = None

_MANAGER_APPROVAL_FIELDS = (
    'manager_response',
    'manager_response_recording',
    'manager_response_recording_filename',
    'manager_attachment',
    'supervisor_signature',
    'supervisor_signature_date',
    'manager_signature',
    'manager_signature_date',
    'ceo_signature',
    'ceo_signature_date',
)


class SpecialApprovalWizardEndDateBuffer(models.Model):
    _inherit = 'special.approval.wizard'

    def _get_manager_approval_field_vals(self):
        self.ensure_one()
        vals = {}
        for field_name in _MANAGER_APPROVAL_FIELDS:
            value = getattr(self, field_name, None)
            if value:
                vals[field_name] = value
        return vals

    def _tracking_write_context(self):
        return dict(
            self.env.context,
            tracking_disable=False,
            mail_notrack=False,
        )

    def _flush_tracking(self):
        """Force pending field-tracking messages to be posted now."""
        self.env.flush_all()
        self.env.cr.precommit.run()

    def _write_manager_approval_state_tracking(self):
        """Log Supervisor -> Manager, then Manager -> CEO as two separate entries."""
        self.ensure_one()
        reservation = self.reservation_id.sudo()
        if not reservation:
            return

        field_vals = self._get_manager_approval_field_vals()
        track_ctx = self._tracking_write_context()

        if reservation.state == 'supervisor':
            # Step 1: state only so chatter shows Supervisor -> Manager clearly.
            reservation.with_context(**track_ctx).write({'state': 'manager'})
            self.write({'state_new': 'manager'})
            self._flush_tracking()

            reservation = reservation.browse(reservation.id)
            if reservation.state != 'manager':
                _logger.error(
                    'Manager approval step 1 failed on reservation %s: state is %s',
                    reservation.id,
                    reservation.state,
                )
                return

            # Step 2: Manager -> CEO (+ 5 min end-date buffer).
            ceo_vals = dict(field_vals, state='ceo')
            new_expire = reservation._get_approval_end_date_buffer()
            if new_expire:
                ceo_vals['expire_date'] = new_expire
            reservation.with_context(**track_ctx).write(ceo_vals)
            self.write({'state_new': 'ceo'})
            self._flush_tracking()

        elif reservation.state == 'manager':
            ceo_vals = dict(field_vals, state='ceo')
            new_expire = reservation._get_approval_end_date_buffer()
            if new_expire:
                ceo_vals['expire_date'] = new_expire
            reservation.with_context(**track_ctx).write(ceo_vals)
            self.write({'state_new': 'ceo'})
            self._flush_tracking()

    def _datetime_equal(self, left, right):
        if not left and not right:
            return True
        if not left or not right:
            return False
        return fields.Datetime.to_datetime(left) == fields.Datetime.to_datetime(right)

    def _retrack_final_approval(self, reservation, old_state, old_expire, old_duration,
                                old_duration_in):
        """Re-apply final approval field changes with tracking enabled."""
        if reservation.state != 'approved':
            return

        final_expire = reservation.expire_date
        final_duration = reservation.special_duration or 0
        final_duration_in = (
            getattr(reservation, 'special_duration_in', None) or 'days'
        )
        old_duration = old_duration or 0
        old_duration_in = old_duration_in or 'days'

        silent_ctx = dict(
            self.env.context,
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        revert_state = 'ceo' if old_state in ('ceo', 'manager', 'approved') else old_state
        revert_vals = {
            'state': revert_state,
            'expire_date': old_expire,
            'special_duration': old_duration,
        }
        if 'special_duration_in' in reservation._fields:
            revert_vals['special_duration_in'] = old_duration_in
        reservation.with_context(**silent_ctx).write(revert_vals)
        self._flush_tracking()
        reservation = reservation.browse(reservation.id)

        track_vals = {'state': 'approved'}
        if not self._datetime_equal(final_expire, old_expire):
            track_vals['expire_date'] = final_expire
        if final_duration != old_duration:
            track_vals['special_duration'] = final_duration
        if (
            'special_duration_in' in reservation._fields
            and final_duration_in != old_duration_in
        ):
            track_vals['special_duration_in'] = final_duration_in

        reservation.with_context(
            tracking_disable=False,
            mail_notrack=False,
        ).write(track_vals)
        self._flush_tracking()

    def action_manager_approve(self):
        self.ensure_one()
        amount = self.amount or 0.0
        if amount > 0 and hasattr(self, '_validate_all_verified'):
            self._validate_all_verified()

        self._write_manager_approval_state_tracking()

        # Skip manager_step state writes (already done above); keep notifications.
        if SpecialApprovalWizardManagerStep is not None:
            return super(
                SpecialApprovalWizardManagerStep,
                self,
            ).action_manager_approve()
        return super().action_manager_approve()

    def action_final_approve(self):
        self.ensure_one()
        reservation = self.reservation_id
        old_state = reservation.state if reservation else False
        old_expire = reservation.expire_date if reservation else False
        old_duration = reservation.special_duration if reservation else 0
        old_duration_in = (
            getattr(reservation, 'special_duration_in', None) if reservation else 'days'
        )

        res = super().action_final_approve()

        if reservation and reservation.state == 'approved':
            try:
                self._retrack_final_approval(
                    reservation,
                    old_state,
                    old_expire,
                    old_duration,
                    old_duration_in,
                )
            except Exception as error:
                _logger.warning(
                    'Could not re-track final approval on reservation %s: %s',
                    reservation.id,
                    error,
                )

        if not res:
            return {'type': 'ir.actions.act_window_close'}
        return res
