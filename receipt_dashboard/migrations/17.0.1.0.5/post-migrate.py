# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backfill receipt.approval.record for payment lines created in the last 7 days
    that don't yet have a receipt approval record.
    Creates each record as the payment line's original creator (not OdooBot/superuser).
    No reservation status filter — covers all reservations regardless of status.
    Covers all reservation types.
    """
    from odoo import api, registry, SUPERUSER_ID

    with registry(cr.dbname).cursor() as new_cr:
        env = api.Environment(new_cr, SUPERUSER_ID, {})
        last_week = datetime.now() - timedelta(days=7)

        payment_lines = env['property.reservation.payment'].search([
            ('create_date', '>=', last_week),
            ('reservation_id', '!=', False),
        ])

        _logger.info(
            'Receipt backfill: found %d payment line(s) created in the last 7 days.',
            len(payment_lines),
        )
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
                _logger.info(
                    'Backfill: skipping payment line %s (ref: %s) — record already exists.',
                    payment_line.id, payment_line.ref_number or 'N/A',
                )
                continue

            try:
                # Use the payment line's creator so activity is assigned to the right user
                creator_uid = payment_line.create_uid.id if payment_line.create_uid else SUPERUSER_ID
                user_env = env(user=creator_uid)

                record = user_env['receipt.approval.record'].create({
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
                    'Backfill: created draft receipt record for payment line %s (ref: %s) on reservation %s (status: %s, creator: %s)',
                    payment_line.id, payment_line.ref_number or 'N/A', reservation.id,
                    reservation.status, creator_uid,
                )
            except Exception as e:
                _logger.warning(
                    'Backfill: failed for payment line %s on reservation %s: %s',
                    payment_line.id, reservation.id, str(e),
                )

        new_cr.commit()
        _logger.info('Receipt backfill complete: %d record(s) created.', total_created)
