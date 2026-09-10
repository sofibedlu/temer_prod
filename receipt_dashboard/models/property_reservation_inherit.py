# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PropertyReservationInherit(models.Model):
    _inherit = 'property.reservation'
    
    # Add pending_approval status to the status selection
    status = fields.Selection(selection_add=[
        ('pending_approval', 'Pending Approval')
    ], ondelete={'pending_approval': 'set default'})
    
    receipt_approval_record_ids = fields.One2many('receipt.approval.record', 'reservation_id', string='Receipt Approval Records')
    
    def approve_reservation(self):
        """Override to create receipt approval records instead of directly reserving"""
        self.ensure_one()

        # Quick reservations with no payment receipts bypass receipt approval and reserve directly
        is_quick = hasattr(self, 'reservation_type_id') and self.reservation_type_id and \
            hasattr(self.reservation_type_id, 'reservation_type') and \
            self.reservation_type_id.reservation_type == 'quick'
        has_receipt = any(
            line.payment_receipt for line in self.payment_line_ids
            if hasattr(line, 'payment_receipt')
        )
        if is_quick and not has_receipt:
            return self.action_reserve_direct()

        if self.property_id.state != 'available':
            other_reserved = self.env['property.reservation'].search([
                ('property_id', '=', self.property_id.id),
                ('status', '=', 'reserved'),
                ('id', '!=', self.id),
            ], limit=1)
            # Allow when converted from quick to regular (we already had the property reserved)
            converted_regular = getattr(self, 'converted_regular', False)
            if other_reserved and not converted_regular:
                raise ValidationError(
                    _("Cannot approve reservation request. Property %s is in %s state") %
                    (self.property_id.name, self.property_id.state))
        
        # Check if payment lines exist
        if not self.payment_line_ids:
            raise ValidationError(_("Cannot approve reservation. Please add payment lines first."))
        
        # Create receipt approval records for each payment line
        # Use sudo() to bypass Receipt Dashboard group requirement when creating from reservation
        ReceiptApprovalRecord = self.env['receipt.approval.record'].sudo()
        created_count = 0

        for payment_line in self.payment_line_ids:
            # Check if receipt approval record already exists for this payment line
            existing = ReceiptApprovalRecord.search([
                ('payment_line_id', '=', payment_line.id),
                ('reservation_id', '=', self.id),
            ], limit=1)

            if not existing:
                record = ReceiptApprovalRecord.create({
                    'reservation_id': self.id,
                    'payment_line_id': payment_line.id,
                    'amount': payment_line.amount,
                    'state': 'draft',
                })
                # Force recompute of payment_receipt to ensure it's stored
                record._compute_payment_receipt()
                record._compute_payment_receipt_filename()
                # Invalidate to trigger recompute of receipt_display
                record.invalidate_recordset(['payment_receipt', 'receipt_display'])
                created_count += 1

        # Reserve the property immediately for regular reservations (original behavior)
        # Receipt approval will only create the receipt
        self.action_reserve_direct()

        # Post message with count of created receipt records
        self.message_post(
            body=_(
                'Reservation reserved. %d draft receipt approval record(s) created for payment verification.'
            ) % created_count,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        
        # Log activity
        self.activity_schedule(
            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            summary=_('Receipt Approval Pending'),
            note=_('Reservation is pending receipt approval. Please review in Receipt Dashboard.'),
            user_id=self.env.user.id,
        )
        
        return True
    
    def write(self, vals):
        """Auto-create draft receipt records when new payment lines are added to a reserved reservation"""
        # Detect reservations being cancelled so we can stamp payment line refs
        cancelling_ids = []
        if vals.get('status') == 'canceled':
            for rec in self:
                if rec.status != 'canceled':
                    cancelling_ids.append(rec.id)

        # Capture existing payment line IDs before write
        existing_payment_ids = {}
        if 'payment_line_ids' in vals:
            for rec in self:
                existing_payment_ids[rec.id] = set(rec.payment_line_ids.ids)

        result = super().write(vals)

        # Stamp [CANCELLED] on all payment line ref numbers when reservation is cancelled
        if cancelling_ids:
            for rec in self.env['property.reservation'].browse(cancelling_ids):
                for line in rec.payment_line_ids:
                    if line.ref_number and '[CANCELLED]' not in line.ref_number:
                        line.sudo().write({'ref_number': line.ref_number + ' [CANCELLED]'})

        # After write, check for newly added payment lines
        if existing_payment_ids:
            ReceiptApprovalRecord = self.env['receipt.approval.record'].sudo()
            for rec in self:
                if rec.id not in existing_payment_ids:
                    continue
                new_line_ids = set(rec.payment_line_ids.ids) - existing_payment_ids[rec.id]
                for line_id in new_line_ids:
                    payment_line = self.env['property.reservation.payment'].browse(line_id)
                    existing = ReceiptApprovalRecord.search([
                        ('payment_line_id', '=', line_id),
                        ('reservation_id', '=', rec.id),
                    ], limit=1)
                    if not existing:
                        record = ReceiptApprovalRecord.create({
                            'reservation_id': rec.id,
                            'payment_line_id': line_id,
                            'amount': payment_line.amount,
                            'state': 'draft',
                        })
                        record._compute_payment_receipt()
                        record._compute_payment_receipt_filename()
                        record.invalidate_recordset(['payment_receipt', 'receipt_display'])
                        _logger.info(
                            'Auto-created draft receipt approval record for new payment line %s on reservation %s',
                            line_id, rec.id
                        )
                        # Log message on the reservation chatter
                        rec.message_post(
                            body=_(
                                'New payment line added. Draft receipt approval record created.\n'
                                'Reference: %s\n'
                                'Amount: %s\n'
                                'Pending approval in Receipt Dashboard.'
                            ) % (
                                payment_line.ref_number or 'N/A',
                                payment_line.amount,
                            ),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                        # Schedule activity on the reservation
                        rec.activity_schedule(
                            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                            summary=_('Receipt Approval Required'),
                            note=_(
                                'A new payment line (Ref: %s, Amount: %s) was added. '
                                'Please review and approve in the Receipt Dashboard.'
                            ) % (payment_line.ref_number or 'N/A', payment_line.amount),
                            user_id=self.env.user.id,
                        )

        return result

    def action_reserve_direct(self):
        """Direct reserve method (bypass approval) - for backward compatibility if needed"""
        self.ensure_one()
        if self.property_id.state != 'available':
            # Allow when property is already 'reserved' if we are the one holding it or we converted quick→regular
            if self.property_id.state == 'reserved':
                other_reserved = self.env['property.reservation'].search([
                    ('property_id', '=', self.property_id.id),
                    ('status', '=', 'reserved'),
                    ('id', '!=', self.id),
                ], limit=1)
                # Allow: no other reservation has it, OR this reservation was converted from quick (we had it)
                converted_regular = getattr(self, 'converted_regular', False)
                if not other_reserved or converted_regular:
                    self.status = 'reserved'
                    if self.crm_lead_id:
                        self.crm_lead_id.action_set_reserved()
                    return True
            raise ValidationError(
                _("Cannot reserve. Property %s is in %s state") %
                (self.property_id.name, self.property_id.state))

        from datetime import timedelta
        channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
        if channel:
            expire_date = self.expire_date + timedelta(hours=3) if self.expire_date else False
            if expire_date:
                channel.message_post(
                    body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date}"),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
        
        self.property_id.sudo().write({'state': 'reserved'})
        self.status = 'reserved'
        
        if self.crm_lead_id:
            self.crm_lead_id.action_set_reserved()
        
        return True

