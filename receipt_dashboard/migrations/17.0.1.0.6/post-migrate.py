# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backfill receipt.approval.record for payment lines created in the last 7 days
    that don't yet have a receipt approval record.
    Uses raw SQL to avoid any ORM filter issues.
    """
    from odoo import api, registry, SUPERUSER_ID

    last_week = datetime.now() - timedelta(days=7)
    last_week_str = last_week.strftime('%Y-%m-%d %H:%M:%S')

    # Find payment lines from last 7 days not yet in receipt_approval_record
    cr.execute("""
        SELECT prp.id, prp.reservation_id, prp.amount, prp.ref_number, prp.create_uid
        FROM property_reservation_payment prp
        WHERE prp.reservation_id IS NOT NULL
          AND prp.create_date >= %s
          AND NOT EXISTS (
              SELECT 1 FROM receipt_approval_record rar
              WHERE rar.payment_line_id = prp.id
                AND rar.reservation_id = prp.reservation_id
          )
    """, (last_week_str,))

    rows = cr.fetchall()
    _logger.info('Receipt backfill: found %d payment line(s) to process.', len(rows))

    if not rows:
        _logger.info('Receipt backfill: nothing to do.')
        return

    with registry(cr.dbname).cursor() as new_cr:
        env = api.Environment(new_cr, SUPERUSER_ID, {})
        total_created = 0

        for (line_id, reservation_id, amount, ref_number, create_uid) in rows:
            try:
                uid = create_uid or SUPERUSER_ID
                user_env = env(user=uid)
                record = user_env['receipt.approval.record'].create({
                    'reservation_id': reservation_id,
                    'payment_line_id': line_id,
                    'amount': amount or 0.0,
                    'state': 'draft',
                })
                record._compute_payment_receipt()
                record._compute_payment_receipt_filename()
                record.invalidate_recordset(['payment_receipt', 'receipt_display'])
                total_created += 1
                _logger.info(
                    'Backfill: created receipt record for payment line %s (ref: %s) on reservation %s (uid: %s)',
                    line_id, ref_number or 'N/A', reservation_id, uid,
                )
            except Exception as e:
                _logger.warning(
                    'Backfill: failed for payment line %s on reservation %s: %s',
                    line_id, reservation_id, str(e),
                )

        new_cr.commit()
        _logger.info('Receipt backfill complete: %d record(s) created.', total_created)
