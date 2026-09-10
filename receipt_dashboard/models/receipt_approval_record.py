# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ReceiptApprovalRecord(models.Model):
    _name = 'receipt.approval.record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Receipt Approval Record'
    _order = 'create_date desc, id desc'

    # Related Fields
    reservation_id = fields.Many2one('property.reservation', string='Reservation', required=True, ondelete='cascade', tracking=True)
    payment_line_id = fields.Many2one('property.reservation.payment', string='Payment Line', required=True, ondelete='cascade', tracking=True)
    
    # Customer Information
    customer_id = fields.Many2one('res.partner', string='Customer', related='reservation_id.partner_id', store=True, readonly=True)
    customer_name = fields.Char(related='customer_id.name', store=True, string='Customer Name', readonly=True)
    
    # Lead Information (from CRM) - may not exist in all installations
    crm_lead_id = fields.Many2one('crm.lead', string='Lead', compute='_compute_crm_lead', store=True, readonly=True)
    lead_customer_id = fields.Many2one('res.partner', string='Lead Customer', compute='_compute_lead_customer', store=True)
    
    # Site and Property
    site_id = fields.Many2one('property.site', string='Site', related='reservation_id.site_id', store=True, readonly=True)
    property_id = fields.Many2one('property.property', string='Property', related='reservation_id.property_id', store=True, readonly=True)
    
    # Payment Information
    amount = fields.Monetary(string='Amount', currency_field='currency_id', compute='_compute_amount', store=True, required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, readonly=True)
    reference_number = fields.Char(string='Reference Number', related='payment_line_id.ref_number', store=True, readonly=True)
    payment_receipt = fields.Binary(string='Receipt File', compute='_compute_payment_receipt', store=True, readonly=True)
    payment_receipt_filename = fields.Char(string='Receipt Filename', compute='_compute_payment_receipt_filename', store=True)
    receipt_display = fields.Binary(string='Receipt', compute='_compute_receipt_display', store=False, readonly=True)
    
    @api.depends('payment_line_id', 'payment_line_id.amount')
    def _compute_amount(self):
        """Compute amount from payment line"""
        for rec in self:
            if rec.payment_line_id and rec.payment_line_id.amount:
                rec.amount = rec.payment_line_id.amount
            else:
                rec.amount = 0.0

    @api.depends('payment_line_id', 'payment_line_id.payment_receipt')
    def _compute_payment_receipt(self):
        """Compute receipt from payment line"""
        for rec in self:
            # Get receipt from payment line
            if rec.payment_line_id:
                # Access payment_receipt directly from payment_line_id
                payment_line = rec.payment_line_id
                if payment_line.payment_receipt:
                    rec.payment_receipt = payment_line.payment_receipt
                else:
                    rec.payment_receipt = False
            else:
                rec.payment_receipt = False
    
    @api.depends('payment_line_id', 'reference_number')
    def _compute_payment_receipt_filename(self):
        """Compute filename for receipt"""
        for rec in self:
            if rec.reference_number:
                rec.payment_receipt_filename = f"Receipt_{rec.reference_number}.pdf"
            else:
                rec.payment_receipt_filename = "Receipt.pdf"
    
    @api.depends('payment_receipt', 'payment_line_id', 'payment_line_id.payment_receipt', 'state')
    def _compute_receipt_display(self):
        """Compute field to show receipt for display (like payment_approval_new)"""
        for rec in self:
            # First try to get from stored payment_receipt
            if rec.payment_receipt:
                rec.receipt_display = rec.payment_receipt
            # If not stored, try to get directly from payment_line_id
            elif rec.payment_line_id and rec.payment_line_id.payment_receipt:
                rec.receipt_display = rec.payment_line_id.payment_receipt
            else:
                rec.receipt_display = False
    
    bank_id = fields.Many2one('bank.configuration', string='Bank', related='payment_line_id.bank_id', store=True, readonly=True)
    document_type_id = fields.Many2one('bank.document.type', string='Document Type', related='payment_line_id.document_type_id', store=True, readonly=True)
    transaction_date = fields.Date(string='Transaction Date', related='payment_line_id.transaction_date', store=True, readonly=True)
    
    # Reservation status mirror (to allow domain filtering)
    reservation_status = fields.Selection(
        related='reservation_id.status',
        string='Reservation Status',
        store=True,
        readonly=True,
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('denied', 'Denied')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Receipt Information
    receipt_id = fields.Many2one('account.move', string='Receipt', readonly=True, copy=False, tracking=True)
    
    # Approval Information
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    denied_by = fields.Many2one('res.users', string='Denied By', readonly=True, tracking=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True, tracking=True)
    denied_date = fields.Datetime(string='Denied Date', readonly=True, tracking=True)
    denial_reason_id = fields.Many2one('receipt.denial.reason', string='Denial Reason', readonly=True, tracking=True)
    denial_reason_description = fields.Text(string='Denial Reason Description', related='denial_reason_id.description', store=True, readonly=True)
    
    @api.depends('reservation_id')
    def _compute_crm_lead(self):
        """Get CRM lead from reservation if available"""
        for rec in self:
            if rec.reservation_id and hasattr(rec.reservation_id, 'crm_lead_id'):
                rec.crm_lead_id = rec.reservation_id.crm_lead_id.id if rec.reservation_id.crm_lead_id else False
            else:
                rec.crm_lead_id = False
    
    @api.depends('crm_lead_id', 'crm_lead_id.partner_id')
    def _compute_lead_customer(self):
        """Get customer from lead if available"""
        for rec in self:
            if rec.crm_lead_id and rec.crm_lead_id.partner_id:
                rec.lead_customer_id = rec.crm_lead_id.partner_id.id
            else:
                rec.lead_customer_id = False
    
    @api.depends('reservation_id', 'reservation_id.property_id')
    def _compute_currency(self):
        """Get currency from property or company"""
        for rec in self:
            if rec.reservation_id and rec.reservation_id.property_id and hasattr(rec.reservation_id.property_id, 'currency_id') and rec.reservation_id.property_id.currency_id:
                rec.currency_id = rec.reservation_id.property_id.currency_id.id
            else:
                rec.currency_id = self.env.company.currency_id.id
    
    def action_approve(self):
        """Approve receipt and create account.move receipt, then reserve property"""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft receipts can be approved.'))

            if rec.receipt_id:
                raise UserError(_("A receipt has already been created for this payment."))

            if rec.amount <= 0:
                raise UserError(_("Payment amount must be greater than zero."))

            # Get or create product (use sudo() to bypass access rights)
            product = self.env['product.product'].sudo().search([('name', '=', 'Property Reservation Payment')], limit=1)
            if not product:
                product = self.env['product.product'].sudo().create({
                    'name': 'Property Reservation Payment',
                    'type': 'service',
                    'list_price': 0.0,
                    'taxes_id': False,
                })

            # Create receipt (account.move with move_type='out_receipt')
            # Use sudo() to bypass access rights - users with Receipt Dashboard role can create receipts
            move_vals = {
                'move_type': 'out_receipt',
                'partner_id': rec.customer_id.id or rec.lead_customer_id.id or rec.reservation_id.partner_id.id,
                'invoice_date': fields.Date.today(),
                'ref': rec.reference_number or '',
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': f"Reservation: {rec.property_id.name or ''} - Ref: {rec.reference_number or ''}",
                    'quantity': 1,
                    'price_unit': rec.amount,
                })],
            }

            invoice = self.env['account.move'].sudo().create(move_vals)

            # Note: Receipt file is stored in receipt.approval.record, not attached to account.move
            # This prevents PDF viewer errors in the accounting receipt view

            # Update receipt approval record
            old_state = rec.state
            rec.write({
                'receipt_id': invoice.id,
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # Post message about approval with detailed tracking (plain text)
            rec.message_post(
                body=_(
                    "Receipt approved by %s\n"
                    "Receipt created: %s\n"
                    "Property reserved: %s\n"
                    "Amount: %s %s\n"
                    "Approved on: %s"
                ) % (
                    rec.approved_by.name or "System",
                    invoice.name or "N/A",
                    rec.property_id.name or "N/A",
                    rec.amount,
                    rec.currency_id.symbol if rec.currency_id else "",
                    rec.approved_date.strftime("%Y-%m-%d %H:%M:%S") if rec.approved_date else "N/A",
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

            # Reserve the property
            if rec.reservation_id.status in ['requested', 'pending_approval']:
                from datetime import timedelta

                # Set property state to reserved
                rec.reservation_id.property_id.sudo().write({'state': 'reserved'})

                # Set reservation status to reserved
                rec.reservation_id.write({'status': 'reserved'})

                # Post message to channel if exists
                channel = self.env['discuss.channel'].search([('name', '=', 'general')], limit=1)
                if channel and rec.reservation_id.expire_date:
                    expire_date = rec.reservation_id.expire_date + timedelta(hours=3)
                    channel.message_post(
                        body=(f"Property {rec.reservation_id.property_id.name} is reserved, reservation will expire on {expire_date}"),
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )

                # Update CRM lead if exists
                if hasattr(rec.reservation_id, 'crm_lead_id') and rec.reservation_id.crm_lead_id:
                    if hasattr(rec.reservation_id.crm_lead_id, 'action_set_reserved'):
                        rec.reservation_id.crm_lead_id.action_set_reserved()

                rec.reservation_id.message_post(
                    body=_('Reservation approved and property reserved via Receipt Dashboard. Receipt: %s') % invoice.name,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

            # Update payment line status
            if rec.payment_line_id:
                rec.payment_line_id.write({
                    'payment_status': 'approved',
                    'is_verifed': True,
                })

            # Always log approval on the reservation chatter (for all statuses)
            rec.reservation_id.message_post(
                body=_(
                    "Receipt APPROVED via Receipt Dashboard\n"
                    "Approved by: %s\n"
                    "Reference: %s\n"
                    "Amount: %s %s\n"
                    "Receipt: %s\n"
                    "Approved on: %s"
                ) % (
                    self.env.user.name,
                    rec.reference_number or 'N/A',
                    rec.amount,
                    rec.currency_id.symbol if rec.currency_id else '',
                    invoice.name or 'N/A',
                    rec.approved_date.strftime("%Y-%m-%d %H:%M:%S") if rec.approved_date else 'N/A',
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

            # Note: Status changes are automatically tracked by Odoo due to tracking=True on state field

            # Mark activity as done
            rec.activity_feedback(['mail.mail_activity_data_todo'])

        return True
    
    def action_bulk_approve(self):
        """Bulk approve multiple draft receipts"""
        if not self:
            raise UserError(_('Please select at least one receipt to approve.'))
        draft_receipts = self.filtered(lambda r: r.state == 'draft')
        if not draft_receipts:
            raise UserError(_('Selected receipts must be in draft state to approve.'))
        draft_receipts.action_approve()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt Dashboard'),
            'res_model': 'receipt.approval.record',
            'view_mode': 'tree,form',
            'domain': [],
            'context': {'search_default_draft': 1},
            'target': 'current',
        }
    
    def action_bulk_deny(self):
        """Bulk deny multiple draft receipts"""
        if not self:
            raise UserError(_('Please select at least one receipt to deny.'))
        draft_receipts = self.filtered(lambda r: r.state == 'draft')
        if not draft_receipts:
            raise UserError(_('Selected receipts must be in draft state to deny.'))
        
        if len(draft_receipts) == 1:
            return draft_receipts.action_deny()
        
        return {
            'name': _('Deny Receipt(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'receipt.deny.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_record_ids': draft_receipts.ids,
                'default_receipt_record_id': draft_receipts[0].id if len(draft_receipts) == 1 else False,
                'bulk_mode': len(draft_receipts) > 1,
            }
        }
    
    def action_deny(self):
        """Open deny wizard"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft receipts can be denied.'))
        
        return {
            'name': _('Deny Receipt'),
            'type': 'ir.actions.act_window',
            'res_model': 'receipt.deny.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_record_id': self.id,
            }
        }
    
    def do_deny_confirm(self, reason_type_id, description):
        """Confirm denial of receipt"""
        for rec in self:
            if rec.state != 'draft':
                continue

            # Create denial reason record (use sudo() to bypass access rights)
            denial_reason = self.env['receipt.denial.reason'].sudo().create({
                'receipt_record_id': rec.id,
                'reason_type_id': reason_type_id,
                'description': description,
            })

            # Update receipt record
            old_state = rec.state
            rec.write({
                'state': 'denied',
                'denied_by': self.env.user.id,
                'denied_date': fields.Datetime.now(),
                'denial_reason_id': denial_reason.id,
            })

            # Post detailed message about denial (plain text)
            reason_type_name = denial_reason.reason_type_id.name if denial_reason.reason_type_id else 'Other'
            rec.message_post(
                body=_(
                    "Receipt denied by %s\n"
                    "Property: %s\n"
                    "Amount: %s %s\n"
                    "Reason Type: %s\n"
                    "Reason Description: %s\n"
                    "Denied on: %s"
                ) % (
                    rec.denied_by.name or "System",
                    rec.property_id.name or "N/A",
                    rec.amount,
                    rec.currency_id.symbol if rec.currency_id else "",
                    reason_type_name,
                    description or "No description provided",
                    rec.denied_date.strftime("%Y-%m-%d %H:%M:%S") if rec.denied_date else "N/A",
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

            # Cancel reservation for all types
            reservation = rec.reservation_id
            if reservation:
                if reservation.property_id and reservation.property_id.state == 'reserved':
                    reservation.property_id.sudo().write({'state': 'available'})
                reservation.write({
                    'status': 'canceled',
                    'canceled_time': fields.Datetime.now(),
                    'canceled_reason': f"Denied via Receipt Dashboard. Reason: {reason_type_name}. {description}",
                })
                reservation.message_post(
                    body=_(
                        "Receipt DENIED via Receipt Dashboard\n"
                        "Denied by: %s\n"
                        "Reference: %s\n"
                        "Amount: %s %s\n"
                        "Reason: %s\n"
                        "Description: %s\n"
                        "Denied on: %s"
                    ) % (
                        rec.denied_by.name or "System",
                        rec.reference_number or 'N/A',
                        rec.amount,
                        rec.currency_id.symbol if rec.currency_id else '',
                        reason_type_name,
                        description or "No description provided",
                        rec.denied_date.strftime("%Y-%m-%d %H:%M:%S") if rec.denied_date else "N/A",
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

            # Append [CANCELLED] to reference number on payment line and approval record
            if rec.payment_line_id and rec.payment_line_id.ref_number:
                current_ref = rec.payment_line_id.ref_number
                if '[CANCELLED]' not in current_ref:
                    cancelled_ref = current_ref + ' [CANCELLED]'
                    rec.payment_line_id.sudo().write({'ref_number': cancelled_ref})
                    # Invalidate stored related field so it recomputes
                    rec.invalidate_recordset(['reference_number'])

            # Mark activity as done
            rec.activity_feedback(['mail.mail_activity_data_todo'])

        return True
    
    def action_open_receipt(self):
        """Open the related receipt (use sudo to bypass access rights)"""
        self.ensure_one()
        if not self.receipt_id:
            raise UserError(_("No receipt has been created yet."))
        
        # Use sudo() to access receipt and bypass access rights
        receipt = self.receipt_id.sudo()
        
        # Return action to open existing receipt
        # Note: We don't post messages to account.move, so its chatter will be empty
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt: %s') % (receipt.name or ''),
            'res_model': 'account.move',
            'res_id': receipt.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'active_id': receipt.id,
                'active_model': 'account.move',
            },
        }
    
    def action_open_reservation(self):
        """Open the related reservation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'property.reservation',
            'res_id': self.reservation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure payment_receipt is computed and stored"""
        records = super().create(vals_list)
        # Force recompute and store payment_receipt for new records
        for record in records:
            if record.payment_line_id:
                # Force recompute of payment_receipt to ensure it's stored
                record._compute_payment_receipt()
                record._compute_payment_receipt_filename()
                # Invalidate to trigger recompute
                record.invalidate_recordset(['payment_receipt', 'payment_receipt_filename'])
            
            # Post detailed message when record is created (plain text)
            record.message_post(
                body=_(
                    "Receipt approval record created\n"
                    "Property: %s\n"
                    "Customer: %s\n"
                    "Amount: %s %s\n"
                    "Bank: %s\n"
                    "Reference: %s\n"
                    "Created on: %s\n"
                    "Status: Draft (Pending Approval)"
                ) % (
                    record.property_id.name or "N/A",
                    record.customer_name or "N/A",
                    record.amount,
                    record.currency_id.symbol if record.currency_id else "",
                    record.bank_id.display_name if record.bank_id else "N/A",
                    record.reference_number or "N/A",
                    record.create_date.strftime("%Y-%m-%d %H:%M:%S") if record.create_date else "N/A",
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            
            # Schedule activity for approval
            if record.state == 'draft':
                record.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary=_('Receipt Approval Required'),
                    note=_('Receipt approval record created. Please review and approve or deny.'),
                    user_id=self.env.user.id,
                )
        return records
    
    def write(self, vals):
        """Override write to recompute receipt when payment_line_id changes and track state changes"""
        # Track state changes for activity logging
        old_states = {}
        if 'state' in vals:
            for rec in self:
                old_states[rec.id] = rec.state

        result = super().write(vals)

        if 'payment_line_id' in vals:
            for rec in self:
                rec._compute_payment_receipt()
                rec._compute_payment_receipt_filename()
                rec.invalidate_recordset(['payment_receipt', 'receipt_display'])

        # Post status change messages
        if 'state' in vals:
            for rec in self:
                old_state = old_states.get(rec.id)
                new_state = rec.state
                if old_state != new_state:
                    status_messages = {
                        'approved': f'Status changed to Approved by {rec.approved_by.name or "System"}',
                        'denied': f'Status changed to Denied by {rec.denied_by.name or "System"}',
                    }
                    if new_state in status_messages:
                        rec.message_post(
                            body=_(
                                "%s\n"
                                "Property: %s\n"
                                "Changed on: %s"
                            ) % (
                                status_messages[new_state],
                                rec.property_id.name or "N/A",
                                fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )

        return result

