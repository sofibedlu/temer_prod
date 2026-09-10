# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .expire_utils import (
    compute_expire_date,
    is_non_working_day,
    push_expire_off_non_working,
)

SKIP_CTX = 'skip_sunday_holiday'
SKIP_WRITE_CTX = 'skip_sunday_holiday_write'

try:
    from odoo.addons.track_time_log_timestamp.models.track_timestamp import (
        PropertyReservationChatter,
    )
except ImportError:
    PropertyReservationChatter = None


class PropertyReservationSkipSundayHoliday(models.Model):
    _inherit = 'property.reservation'

    def _duration_in_for_expire(self):
        self.ensure_one()
        if self.reservation_type_id:
            return self.reservation_type_id.duration_in
        return 'days'

    def _skip_sunday_holiday_applies(self):
        """Do not adjust reservations on properties already in Pending Sales."""
        self.ensure_one()
        return not (
            self.property_id
            and self.property_id.state == 'pending_sales'
        )

    def _expire_on_non_working_day(self):
        """True when expire_date falls on Sunday or a public holiday."""
        self.ensure_one()
        if not self.expire_date or self._duration_in_for_expire() in ('minutes', 'hours'):
            return False
        return is_non_working_day(
            self.env, fields.Datetime.to_datetime(self.expire_date).date()
        )

    def _apply_sunday_holiday(self):
        for rec in self:
            if not rec._skip_sunday_holiday_applies():
                continue
            if not rec._expire_on_non_working_day():
                continue
            fixed = push_expire_off_non_working(
                rec.env, rec.expire_date, rec._duration_in_for_expire()
            )
            raw = fields.Datetime.to_datetime(rec.expire_date)
            if fixed == raw:
                continue
            rec.with_context(**{SKIP_CTX: True}).write({
                'expire_date': fields.Datetime.to_string(fixed),
            })
            if rec.property_id:
                rec.property_id.with_context(**{SKIP_CTX: True}).write({
                    'reservation_end_date': fixed,
                })

    @api.model
    def _fix_all_sunday_holiday(self):
        """One-time: fix expire dates on Sunday/holiday (not on pending_sales properties)."""
        reservations = self.search([
            ('expire_date', '!=', False),
            ('status', 'not in', ['expired', 'canceled', 'sold']),
            ('property_id.state', '!=', 'pending_sales'),
        ])
        reservations._apply_sunday_holiday()

    def get_expire_date(self, reservation_type_id):
        reservation_type = self.env['property.reservation.configuration'].browse(
            reservation_type_id
        )
        if not reservation_type:
            return super().get_expire_date(reservation_type_id)
        return compute_expire_date(
            self.env,
            fields.Datetime.now(),
            reservation_type.duration or 0,
            reservation_type.duration_in,
        )

    def _write_bypass_track_timestamp(self, vals):
        """Skip slow per-field chatter posts during final approve."""
        if PropertyReservationChatter is not None:
            return super(PropertyReservationChatter, self).write(vals)
        return super(PropertyReservationSkipSundayHoliday, self).write(vals)

    def write(self, vals):
        if self.env.context.get(SKIP_WRITE_CTX):
            return self._write_bypass_track_timestamp(vals)

        res = super().write(vals)
        if (
            self.env.context.get(SKIP_CTX)
            or 'expire_date' not in vals
        ):
            return res
        to_fix = self.filtered(
            lambda r: r._skip_sunday_holiday_applies() and r._expire_on_non_working_day()
        )
        if to_fix:
            to_fix._apply_sunday_holiday()
        return res

    def approve_reservation(self):
        res = super().approve_reservation()
        self._apply_sunday_holiday()
        return res

    def action_convert_to_regular(self):
        convert_context = {}
        for rec in self:
            regular_type = self.env['property.reservation.configuration'].search(
                [('reservation_type', '=', 'regular')], limit=1
            )
            convert_context[rec.id] = {
                'base_dt': fields.Datetime.now(),
                'duration': (regular_type.duration or 0) if regular_type else 0,
                'duration_in': regular_type.duration_in if regular_type else 'days',
            }

        res = super().action_convert_to_regular()

        for rec in self:
            ctx = convert_context.get(rec.id)
            if not ctx or ctx['duration_in'] in ('minutes', 'hours'):
                continue
            expire_date = compute_expire_date(
                rec.env, ctx['base_dt'], ctx['duration'], ctx['duration_in']
            )
            rec.with_context(**{SKIP_CTX: True}).write({
                'expire_date': fields.Datetime.to_string(expire_date),
            })
            if rec.property_id:
                rec.property_id.with_context(**{SKIP_CTX: True}).write({
                    'reservation_end_date': expire_date,
                })

        return res
