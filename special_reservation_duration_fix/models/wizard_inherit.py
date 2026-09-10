# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, _
from odoo.exceptions import ValidationError

BLOCKED_STATUSES = ('expired', 'canceled', 'sold')


def _add_sundays(base_dt, new_expire):
    """Count Sundays between base_dt and new_expire and add them as extra days."""
    sunday_count = 0
    cursor = base_dt
    while cursor <= new_expire:
        if cursor.weekday() == 6:  # Sunday
            sunday_count += 1
        cursor += timedelta(days=1)
    if sunday_count:
        new_expire = new_expire + timedelta(days=sunday_count)
    return new_expire


class SpecialApprovalWizardDurationFix(models.Model):
    _inherit = 'special.approval.wizard'

    def _check_reservation_not_expired(self):
        """Raise if the linked reservation is expired, canceled, or sold."""
        if self.reservation_id and self.reservation_id.status in BLOCKED_STATUSES:
            raise ValidationError(_(
                "Cannot proceed: the reservation is %s. "
                "Special approval actions are not allowed on expired, canceled, or sold reservations."
            ) % self.reservation_id.status)

    def action_submit(self):
        self._check_reservation_not_expired()
        if self.reservation_id and self.duration_in:
            self.reservation_id.sudo().write({'special_duration_in': self.duration_in})
        return super().action_submit()

    def action_supervisor_approve(self):
        self._check_reservation_not_expired()
        if self.reservation_id and self.duration_in:
            self.reservation_id.sudo().write({'special_duration_in': self.duration_in})
        return super().action_supervisor_approve()

    def action_manager_approve(self):
        self._check_reservation_not_expired()
        if self.reservation_id and self.duration_in:
            self.reservation_id.sudo().write({'special_duration_in': self.duration_in})
        return super().action_manager_approve()

    def action_final_approve(self):
        self._check_reservation_not_expired()
        res = super().action_final_approve()

        # Apply Sunday skip to the expire_date set by super(), matching
        # the same logic used in get_expire_date() for regular reservations.
        reservation = self.reservation_id
        if reservation and reservation.expire_date:
            duration = self.duration or 0
            duration_in = self.duration_in or 'days'
            if duration > 0:
                # Recalculate the base start point (before the duration was added)
                # so we count Sundays over the same window super() used.
                base_dt = fields.Datetime.to_datetime(reservation.expire_date)
                if duration_in == 'minutes':
                    window_start = base_dt - timedelta(minutes=duration)
                elif duration_in == 'hours':
                    window_start = base_dt - timedelta(hours=duration)
                elif duration_in == 'days':
                    window_start = base_dt - timedelta(days=duration)
                elif duration_in == 'weeks':
                    window_start = base_dt - timedelta(weeks=duration)
                elif duration_in == 'months':
                    window_start = base_dt - relativedelta(months=duration)
                else:
                    window_start = base_dt

                adjusted = _add_sundays(window_start, base_dt)
                if adjusted != base_dt:
                    reservation.write({
                        'expire_date': fields.Datetime.to_string(adjusted)
                    })

        return res


class PropertyReservationWizardOpener(models.Model):
    _inherit = 'property.reservation'

    def action_view_special_approval(self):
        """Block if expired/canceled, otherwise inject saved duration_in."""
        if self.status in BLOCKED_STATUSES:
            raise ValidationError(_(
                "Cannot open Special Approval Form: the reservation is %s."
            ) % self.status)
        action = super().action_view_special_approval()
        if isinstance(action, dict) and action.get('context') is not None:
            action['context']['default_duration_in'] = self.special_duration_in or 'days'
        return action

    def action_request_special_approval(self):
        """Block if expired/canceled, otherwise inject saved duration_in."""
        if self.status in BLOCKED_STATUSES:
            raise ValidationError(_(
                "Cannot request Special Approval: the reservation is %s."
            ) % self.status)
        action = super().action_request_special_approval()
        if isinstance(action, dict) and action.get('context') is not None:
            action['context']['default_duration_in'] = self.special_duration_in or 'days'
        return action
