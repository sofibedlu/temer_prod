# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SpecialApprovalWizardManagerStep(models.Model):
    _inherit = 'special.approval.wizard'

    def _get_manager_users(self):
        """Return all active users in the Call Center Manager group."""
        try:
            group = self.env.ref('special_reservation.group_manager')
            return group.users.filtered(lambda u: u.active)
        except Exception:
            return self.env['res.users'].sudo().browse()

    def action_supervisor_approve(self):
        """
        Override supervisor approve:
        1. Block if any payment line is not yet verified (mirrors the check that
           special_reservation_payment places on action_manager_approve — the check
           must live here now that the supervisor button correctly calls
           action_supervisor_approve instead of action_manager_approve).
        2. Notify Call Center Manager group users that their approval step is next.
        """
        self.ensure_one()
        # Run payment verification if special_reservation_payment is installed.
        # _validate_all_verified is defined on the model by that module.
        amount = self.amount or 0.0
        if amount > 0 and hasattr(self, '_validate_all_verified'):
            self._validate_all_verified()

        res = super().action_supervisor_approve()
        try:
            reservation = self.reservation_id
            property_name = reservation.property_id.name or ''

            manager_users = self._get_manager_users()
            subject = _('Special Reservation Needs Manager Approval')
            body = _(
                'Special reservation for %s has been approved by the supervisor '
                'and is now waiting for your manager approval.'
            ) % property_name

            if manager_users:
                self._notify_users(manager_users, subject, body)

            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('Manager step notification after supervisor approve failed: %s', e)
        return res

    def action_manager_approve(self):
        """
        Manager approves — moves the reservation to 'manager' state so the chatter
        correctly logs "Supervisor Approval → Manager Approval".
        The base action_manager_approve writes state='ceo' directly, which causes
        the log to skip the Manager Approval step entirely, so we do NOT call
        super() here. Instead we replicate the field-write logic with state='manager'
        and handle CEO notifications ourselves.
        """
        self.ensure_one()
        if self.reservation_id:
            vals = {'state': 'manager'}
            for field in [
                'manager_response', 'manager_response_recording',
                'manager_response_recording_filename', 'manager_attachment',
                'supervisor_signature', 'supervisor_signature_date',
                'manager_signature', 'manager_signature_date',
                'ceo_signature', 'ceo_signature_date',
            ]:
                v = getattr(self, field, None)
                if v:
                    vals[field] = v
            self.reservation_id.write(vals)
            self.write({'state_new': 'manager'})

        # Notify CEO group users that final approval is now required
        try:
            reservation = self.reservation_id
            property_name = reservation.property_id.name or ''

            ceo_users = self._get_ceo_users()
            subject = _('Special Reservation Needs Final Approval')
            body = _(
                'Special reservation for %s has been approved by the manager '
                'and is now waiting for your final approval.'
            ) % property_name

            if ceo_users:
                self._notify_users(ceo_users, subject, body)

            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('CEO notification after manager approve failed: %s', e)

        return {'type': 'ir.actions.act_window_close'}
