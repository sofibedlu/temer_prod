# -*- coding: utf-8 -*-
"""
Migration 17.0.1.0.8
Backfill reservation chatter logs for existing approved/denied receipt records
that were processed before this logging was added.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    records = env['receipt.approval.record'].search([
        ('state', 'in', ['approved', 'denied']),
        ('reservation_id', '!=', False),
    ])

    _logger.info('Backfilling reservation chatter logs for %d receipt records...', len(records))

    for rec in records:
        reservation = rec.reservation_id
        if not reservation:
            continue

        # Check if a log already exists on the reservation for this receipt
        # to avoid duplicating on re-run
        existing_logs = reservation.message_ids.filtered(
            lambda m: rec.reference_number and rec.reference_number in (m.body or '')
                      and 'Receipt Dashboard' in (m.body or '')
        )
        if existing_logs:
            continue

        if rec.state == 'approved':
            approved_date_str = rec.approved_date.strftime("%Y-%m-%d %H:%M:%S") if rec.approved_date else 'N/A'
            receipt_name = rec.receipt_id.name if rec.receipt_id else 'N/A'
            # Post as the actual approver user using with_user()
            poster = reservation.with_user(rec.approved_by.id) if rec.approved_by else reservation.sudo()
            poster.message_post(
                body=(
                    "Receipt APPROVED via Receipt Dashboard\n"
                    "Approved by: %s\n"
                    "Reference: %s\n"
                    "Amount: %s %s\n"
                    "Receipt: %s\n"
                    "Approved on: %s"
                ) % (
                    rec.approved_by.name if rec.approved_by else 'System',
                    rec.reference_number or 'N/A',
                    rec.amount,
                    rec.currency_id.symbol if rec.currency_id else '',
                    receipt_name,
                    approved_date_str,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        elif rec.state == 'denied':
            denied_date_str = rec.denied_date.strftime("%Y-%m-%d %H:%M:%S") if rec.denied_date else 'N/A'
            reason_type_name = rec.denial_reason_id.reason_type_id.name if rec.denial_reason_id and rec.denial_reason_id.reason_type_id else 'Other'
            description = rec.denial_reason_description or 'No description provided'
            # Post as the actual denier user using with_user()
            poster = reservation.with_user(rec.denied_by.id) if rec.denied_by else reservation.sudo()
            poster.message_post(
                body=(
                    "Receipt DENIED via Receipt Dashboard\n"
                    "Denied by: %s\n"
                    "Reference: %s\n"
                    "Amount: %s %s\n"
                    "Reason: %s\n"
                    "Description: %s\n"
                    "Denied on: %s"
                ) % (
                    rec.denied_by.name if rec.denied_by else 'System',
                    rec.reference_number or 'N/A',
                    rec.amount,
                    rec.currency_id.symbol if rec.currency_id else '',
                    reason_type_name,
                    description,
                    denied_date_str,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    _logger.info('Backfill complete.')
