# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backfill receipt.approval.record for ALL reservations that have payment lines
    but no existing receipt approval record.
    No date or status filter — covers everything missed before this module was deployed.
    Safe to run multiple times — skips lines that already have a record.
    """
    from odoo import api, registry, SUPERUSER_ID

    with registry(cr.dbname).cursor() as new_cr:
        env = api.Environment(new_cr, SUPERUSER_ID, {})

        # Get all payment lines that don't have a receipt approval record yet
        cr.execute("""
            SELECT prp.id, prp.reservation_id, prp.amount, prp.ref_number
            FROM property_reservation_payment prp
            WHERE NOT EXISTS (
                SELECT 1 FROM receipt_approval_record rar
                WHERE rar.payment_line_id = prp.id
                  AND rar.reservation_id = prp.reservation_id
            )
            AND prp.reservation_id IS NOT NULL
        """)
        rows = cr.fetchall()

        _logger.info('Receipt backfill: found %d payment line(s) without receipt approval records.', len(rows))
        total_created = 0

        for (line_id, reservation_id, amount, ref_number) in rows:
            try:
                record = env['receipt.approval.record'].create({
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
                    'Backfill: created draft receipt record for payment line %s (ref: %s) on reservation %s',
                    line_id, ref_number or 'N/A', reservation_id,
                )
            except Exception as e:
                _logger.warning(
                    'Backfill: failed to create receipt record for payment line %s on reservation %s: %s',
                    line_id, reservation_id, str(e),
                )

        new_cr.commit()
        _logger.info('Receipt backfill complete: %d record(s) created.', total_created)
