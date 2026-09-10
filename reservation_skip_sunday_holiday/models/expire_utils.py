# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time

from dateutil.relativedelta import relativedelta
from odoo import fields

MAX_ADJUST_ITERATIONS = 366
MAX_ADJUST_DAY_SPAN = 400


def _to_datetime(dt):
    return fields.Datetime.to_datetime(dt)


def add_duration(base_dt, duration, duration_in):
    base_dt = _to_datetime(base_dt)
    duration = duration or 0
    if duration_in == 'minutes':
        return base_dt + timedelta(minutes=duration)
    if duration_in == 'hours':
        return base_dt + timedelta(hours=duration)
    if duration_in == 'days':
        return base_dt + timedelta(days=duration)
    if duration_in == 'weeks':
        return base_dt + timedelta(weeks=duration)
    if duration_in == 'months':
        return base_dt + relativedelta(months=duration)
    return base_dt


def _holiday_dates_in_range(env, start_date, end_date):
    """Load public holidays for a date range in one query."""
    if start_date > end_date or 'resource.calendar.leaves' not in env:
        return set()
    day_start = datetime.combine(start_date, time.min)
    day_end = datetime.combine(end_date, time.max)
    leaves = env['resource.calendar.leaves'].sudo().search([
        ('resource_id', '=', False),
        ('date_from', '<=', fields.Datetime.to_string(day_end)),
        ('date_to', '>=', fields.Datetime.to_string(day_start)),
    ])
    holidays = set()
    for leave in leaves:
        cur = max(fields.Datetime.to_datetime(leave.date_from).date(), start_date)
        end = min(fields.Datetime.to_datetime(leave.date_to).date(), end_date)
        while cur <= end:
            holidays.add(cur)
            cur += timedelta(days=1)
    return holidays


def _is_public_holiday(env, day_date, holiday_dates=None):
    if holiday_dates is not None:
        return day_date in holiday_dates
    if 'resource.calendar.leaves' not in env:
        return False
    day_start = datetime.combine(day_date, time.min)
    day_end = datetime.combine(day_date, time.max)
    return bool(
        env['resource.calendar.leaves'].sudo().search_count([
            ('resource_id', '=', False),
            ('date_from', '<=', day_end),
            ('date_to', '>=', day_start),
        ])
    )


def is_non_working_day(env, day_date, holiday_dates=None):
    return day_date.weekday() == 6 or _is_public_holiday(
        env, day_date, holiday_dates=holiday_dates
    )


def _count_non_working_days(env, start_date, end_date, holiday_dates=None):
    """Count Sundays/holidays in [start_date, end_date) (end exclusive)."""
    if start_date >= end_date:
        return 0
    if holiday_dates is None:
        holiday_dates = _holiday_dates_in_range(env, start_date, end_date)
    count = 0
    cursor = start_date
    while cursor < end_date:
        if is_non_working_day(env, cursor, holiday_dates=holiday_dates):
            count += 1
        cursor += timedelta(days=1)
    return count


def adjust_expire_skip(env, base_dt, expire_dt, duration_in=None):
    """Extend expire for each Sunday/holiday in the reservation window (once)."""
    if duration_in in ('minutes', 'hours'):
        return _to_datetime(expire_dt)

    base_dt = _to_datetime(base_dt)
    expire_dt = _to_datetime(expire_dt)

    if (expire_dt.date() - base_dt.date()).days > MAX_ADJUST_DAY_SPAN:
        return push_expire_off_non_working(env, expire_dt, duration_in)

    base_date = base_dt.date()
    original_end = expire_dt.date()

    # Count non-working days inside the original window only (no re-count loop).
    extra = _count_non_working_days(env, base_date, original_end)
    if extra:
        expire_dt = expire_dt + timedelta(days=extra)
        # New days added after original_end may themselves be non-working.
        tail_extra = _count_non_working_days(
            env, original_end, expire_dt.date()
        )
        if tail_extra:
            expire_dt = expire_dt + timedelta(days=tail_extra)

    return push_expire_off_non_working(env, expire_dt, duration_in)


def push_expire_off_non_working(env, expire_dt, duration_in=None):
    if duration_in in ('minutes', 'hours'):
        return _to_datetime(expire_dt)
    expire_dt = _to_datetime(expire_dt)
    holiday_dates = _holiday_dates_in_range(
        env, expire_dt.date(), expire_dt.date() + timedelta(days=31)
    )
    for _ in range(MAX_ADJUST_ITERATIONS):
        if not is_non_working_day(env, expire_dt.date(), holiday_dates=holiday_dates):
            break
        expire_dt += timedelta(days=1)
    return expire_dt


def compute_expire_date(env, base_dt, duration, duration_in):
    expire_dt = add_duration(base_dt, duration, duration_in)
    return adjust_expire_skip(env, base_dt, expire_dt, duration_in)
