# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backfill missing receipt.approval.record entries using ORM so all
    computed/related fields (customer, site, property, reference, etc.) are set.

    Only targets reservations that already have at least one receipt.approval.record
    (meaning they went through the receipt dashboard flow before).
    """
    from odoo import api, registry, SUPERUSER_ID

    with registry(cr.dbname).cursor() as new_cr:
        env = api.Environment(new_cr, SUPERUSER_ID, {})

        # Find reservations that already have at least one receipt record
        existing_records = env['receipt.approval.record'].search([])
        reservation_ids = existing_records.mapped('reservation_id').ids

        if not reservation_ids:
            _logger.info('Receipt backfill: no reservations with existing receipt records, skipping.')
            return

        reservations = env['property.reservation'].browse(reservation_ids)
        total_created = 0

        for res in reservations:
            # Only regular reservations
            if hasattr(res, 'reservation_type_id') and res.reservation_type_id and \
               hasattr(res.reservation_type_id, 'reservation_type') and \
               res.reservation_type_id.reservation_type != 'regular':
                continue

            for payment_line in res.payment_line_ids:
                existing = env['receipt.approval.record'].search([
                    ('payment_line_id', '=', payment_line.id),
                    ('reservation_id', '=', res.id),
                ], limit=1)
                if not existing:
                    record = env['receipt.approval.record'].create({
                        'reservation_id': res.id,
                        'payment_line_id': payment_line.id,
                        'amount': payment_line.amount,
                        'state': 'draft',
                    })
                    record._compute_payment_receipt()
                    record._compute_payment_receipt_filename()
                    record.invalidate_recordset(['payment_receipt', 'receipt_display'])
                    total_created += 1
                    _logger.info(
                        'Receipt backfill: created draft record for payment line %s (ref: %s) on reservation %s',
                        payment_line.id, payment_line.ref_number, res.id
                    )

        new_cr.commit()
        _logger.info('Receipt backfill complete: %d record(s) created.', total_created)
