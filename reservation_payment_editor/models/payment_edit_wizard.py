# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PropertyReservationPaymentEditMixin(models.Model):
    """Add the 'Edit Payment' button action to property.reservation.payment."""
    _inherit = 'property.reservation.payment'

    def action_open_edit_wizard(self):
        self.ensure_one()
        return {
            'name': _('Edit Payment Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'reservation.payment.edit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
                'active_id': self.id,
            },
        }


class ReservationPaymentEditWizard(models.TransientModel):
    _name = 'reservation.payment.edit.wizard'
    _description = 'Edit Reservation Payment'

    payment_id = fields.Many2one(
        'property.reservation.payment',
        string='Payment',
        required=True,
        ondelete='cascade',
    )

    # Read-only info fields so user knows what they're editing
    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        related='payment_id.reservation_id',
        readonly=True,
    )
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='payment_id.property_id',
        readonly=True,
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='payment_id.customer_id',
        readonly=True,
    )
    payment_status = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Verified'),
        ('canceled', 'Canceled'),
    ], string='Payment Status')

    # Editable fields — pre-filled from current payment values
    ref_number = fields.Char(string='Reference Number')
    bank_id = fields.Many2one('bank.configuration', string='Bank')
    document_type_id = fields.Many2one('bank.document.type', string='Document Type')
    amount = fields.Float(string='Amount', digits=(16, 2))
    transaction_date = fields.Date(string='Transaction Date')
    payment_receipt = fields.Binary(string='Payment Receipt')
    payment_receipt_filename = fields.Char(string='Receipt Filename')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        payment_id = (
            self._context.get('default_payment_id')
            or self._context.get('active_id')
        )
        if payment_id:
            payment = self.env['property.reservation.payment'].browse(payment_id)
            if payment.exists():
                res.update({
                    'payment_id': payment.id,
                    'ref_number': payment.ref_number,
                    'bank_id': payment.bank_id.id if payment.bank_id else False,
                    'document_type_id': payment.document_type_id.id if payment.document_type_id else False,
                    'amount': payment.amount,
                    'transaction_date': payment.transaction_date,
                    'payment_receipt': payment.payment_receipt,
                    'payment_receipt_filename': (
                        f"Receipt_{payment.ref_number}.pdf" if payment.ref_number else "Receipt.pdf"
                    ),
                    'payment_status': payment.payment_status,
                })
        return res

    def action_save(self):
        """Write changed fields to the payment line.
        The ORM write triggers the cascade in receipt_dashboard so
        the linked receipt approval record updates automatically.
        """
        self.ensure_one()

        if not self.payment_id:
            raise UserError(_('No payment selected.'))

        if self.amount <= 0:
            raise ValidationError(_('Amount must be greater than zero.'))

        if not self.ref_number or not self.ref_number.strip():
            raise ValidationError(_('Reference Number cannot be empty.'))

        payment = self.payment_id

        # Build only the values that actually changed
        vals = {}

        if self.ref_number != payment.ref_number:
            vals['ref_number'] = self.ref_number.strip()

        if self.bank_id.id != payment.bank_id.id:
            vals['bank_id'] = self.bank_id.id

        if self.document_type_id.id != payment.document_type_id.id:
            vals['document_type_id'] = self.document_type_id.id

        if self.amount != payment.amount:
            vals['amount'] = self.amount

        if self.transaction_date != payment.transaction_date:
            vals['transaction_date'] = self.transaction_date

        if self.payment_receipt != payment.payment_receipt:
            vals['payment_receipt'] = self.payment_receipt

        if self.payment_status != payment.payment_status:
            vals['payment_status'] = self.payment_status

        if not vals:
            return {'type': 'ir.actions.act_window_close'}

        # Capture old values for the log before writing
        old_values = {
            'ref_number':       payment.ref_number,
            'bank_id':          payment.bank_id,
            'document_type_id': payment.document_type_id,
            'amount':           payment.amount,
            'transaction_date': payment.transaction_date,
            'payment_status':   payment.payment_status,
        }

        # Write through ORM
        payment.sudo().write(vals)

        _logger.info(
            'ReservationPaymentEditWizard: updated payment %s — changed fields: %s',
            payment.id, list(vals.keys()),
        )

        # Post chatter log showing every changed field (old → new)
        self._post_edit_log(payment, vals, old_values)

        # Cascade to receipt_approval_record
        self._sync_receipt_records(payment)

        return {'type': 'ir.actions.act_window_close'}

    def _post_edit_log(self, payment, vals, old_values):
        """Post a chatter message on the payment listing every changed field."""
        label_map = {
            'ref_number':       _('Reference Number'),
            'bank_id':          _('Bank'),
            'document_type_id': _('Document Type'),
            'amount':           _('Amount'),
            'transaction_date': _('Transaction Date'),
            'payment_receipt':  _('Payment Receipt'),
            'payment_status':   _('Payment Status'),
        }

        status_labels = {
            'draft': 'Draft',
            'requested': 'Requested',
            'approved': 'Verified',
            'canceled': 'Canceled',
        }

        lines = []
        for field_key, label in label_map.items():
            if field_key not in vals:
                continue
            if field_key == 'payment_receipt':
                lines.append(f"• {label}: Receipt file updated")
            elif field_key == 'payment_status':
                old = status_labels.get(old_values.get('payment_status', ''), old_values.get('payment_status', '—'))
                new = status_labels.get(vals['payment_status'], vals['payment_status'])
                lines.append(f"• {label}: {old} → {new}")
            elif field_key == 'bank_id':
                old = old_values['bank_id'].display_name if old_values['bank_id'] else '—'
                new = payment.bank_id.display_name if payment.bank_id else '—'
                lines.append(f"• {label}: {old} → {new}")
            elif field_key == 'document_type_id':
                old = old_values['document_type_id'].display_name if old_values['document_type_id'] else '—'
                new = payment.document_type_id.display_name if payment.document_type_id else '—'
                lines.append(f"• {label}: {old} → {new}")
            else:
                old = old_values.get(field_key, '—')
                new = vals[field_key]
                lines.append(f"• {label}: {old} → {new}")

        if not lines:
            return

        body = _("Payment edited by %s:\n%s") % (
            self.env.user.name,
            "\n".join(lines),
        )
        payment.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _sync_receipt_records(self, payment):
        """Force-sync all stored fields on linked receipt.approval.record rows.

        Works in two modes:
        - If receipt_dashboard has been upgraded: calls action_sync_from_source()
          which uses env.add_to_compute for every mirrored field.
        - If not yet upgraded: manually queues recompute for each stored
          related/computed field and flushes to DB.
        """
        if 'receipt.approval.record' not in self.env:
            return

        try:
            receipt_records = self.env['receipt.approval.record'].sudo().search([
                ('payment_line_id', '=', payment.id),
            ])
            if not receipt_records:
                return

            # Prefer the dedicated sync method added in receipt_dashboard upgrade
            if hasattr(receipt_records, 'action_sync_from_source'):
                receipt_records.action_sync_from_source()
                _logger.info(
                    'ReservationPaymentEditWizard: synced %d receipt record(s) '
                    'via action_sync_from_source for payment %s',
                    len(receipt_records), payment.id,
                )
                return

            # Fallback: queue every stored related/computed field for recompute
            sync_field_names = [
                'reference_number', 'document_type_id', 'bank_id',
                'amount', 'transaction_date', 'payment_receipt',
                'payment_receipt_filename', 'receipt_display',
                'customer_id', 'customer_name', 'site_id', 'property_id',
                'reservation_status', 'currency_id',
                'crm_lead_id', 'lead_customer_id',
            ]
            for fname in sync_field_names:
                if fname not in receipt_records._fields:
                    continue
                field = receipt_records._fields[fname]
                if field.store and (field.compute or field.related):
                    self.env.add_to_compute(field, receipt_records)

            self.env.flush_all()
            _logger.info(
                'ReservationPaymentEditWizard: synced %d receipt record(s) '
                'via add_to_compute fallback for payment %s',
                len(receipt_records), payment.id,
            )

        except Exception as e:
            _logger.warning(
                'ReservationPaymentEditWizard: could not sync receipt records '
                'for payment %s: %s', payment.id, str(e),
            )
