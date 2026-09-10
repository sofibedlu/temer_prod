# -*- coding: utf-8 -*-

from . import models
from . import wizard


def _backfill_receipt_records(env):
    import logging
    from datetime import datetime, timedelta
    _logger = logging.getLogger(__name__)

    last_week = datetime.now() - timedelta(days=7)

    payment_lines = env['property.reservation.payment'].search([
        ('create_date', '>=', last_week),
        ('reservation_id', '!=', False),
    ])

    _logger.info('Receipt backfill: found %d payment line(s) from last 7 days.', len(payment_lines))
    total_created = 0

    for payment_line in payment_lines:
        reservation = payment_line.reservation_id
        if not reservation:
            continue
        existing = env['receipt.approval.record'].search([
            ('payment_line_id', '=', payment_line.id),
            ('reservation_id', '=', reservation.id),
        ], limit=1)
        if existing:
            continue
        try:
            creator_uid = payment_line.create_uid.id if payment_line.create_uid else env.uid
            record = env(user=creator_uid)['receipt.approval.record'].create({
                'reservation_id': reservation.id,
                'payment_line_id': payment_line.id,
                'amount': payment_line.amount or 0.0,
                'state': 'draft',
            })
            record._compute_payment_receipt()
            record._compute_payment_receipt_filename()
            record.invalidate_recordset(['payment_receipt', 'receipt_display'])
            total_created += 1
            _logger.info(
                'Backfill: created receipt record for payment line %s (ref: %s) on reservation %s',
                payment_line.id, payment_line.ref_number or 'N/A', reservation.id,
            )
        except Exception as e:
            _logger.warning(
                'Backfill: failed for payment line %s on reservation %s: %s',
                payment_line.id, reservation.id, str(e),
            )

    _logger.info('Receipt backfill complete: %d record(s) created.', total_created)


def post_init_hook(env):
    _backfill_receipt_records(env)


def post_migrate_hook(env):
    _backfill_receipt_records(env)
