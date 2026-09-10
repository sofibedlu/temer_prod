# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PaymentApprovalRecord(models.Model):
    _name = 'payment.approval.record'
    _inherit = ['mail.thread']
    _description = 'Payment Approval Record'
    _order = 'payment_date desc, id desc'

    installment_id = fields.Many2one('collection.installment', string='Installment', required=True, ondelete='cascade')
    collection_id = fields.Many2one('collection.order', related='installment_id.collection_id', store=True, string='Collection Order', readonly=True)
    partner_id = fields.Many2one('res.partner', related='installment_id.collection_id.partner_id', store=True, string='Customer', readonly=True)
    customer_name = fields.Char(related='partner_id.name', store=True, string='Customer Name', readonly=True)
    
    amount = fields.Monetary(string='Payment Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='installment_id.currency_id', store=True, readonly=True)
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.today)
    
    journal_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check')
    ], string='Payment Method', required=True, default='bank')
    bank_id = fields.Many2one('bank.configuration', string="Bank")
    document_type_id = fields.Many2one('bank.document.type', string="Document Type")
    payment_receipt = fields.Binary(string="Payment Receipt")
    reference_number = fields.Char(string="Reference Number")
    reference = fields.Char(string='Reference No')
    
    apply_discount = fields.Boolean(string="Apply Discount", default=False)
    discount_percentage = fields.Float(string="Discount (%)")
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id', default=0.0)
    
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('denied', 'Denied')
    ], string='Status', default='draft', required=True, tracking=True)
    
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    installment_payment_id = fields.Many2one(
        'collection.installment.payment',
        string='Installment Payment',
        compute='_compute_installment_payment_link',
        store=False,
        readonly=True,
    )
    # Computed fields for approved payments
    approved_bank_id = fields.Many2one(
        'bank.configuration',
        string="Bank",
        compute='_compute_approved_fields',
        store=False,
        readonly=True
    )
    approved_reference_number = fields.Char(
        string="Reference Number",
        compute='_compute_approved_fields',
        store=False,
        readonly=True
    )
    approved_receipt = fields.Binary(
        string="Payment Receipt",
        readonly=True
    )
    receipt_display = fields.Binary(
        string="Receipt",
        compute='_compute_receipt_display',
        store=False,
        readonly=True
    )
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    denied_by = fields.Many2one('res.users', string='Denied By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    denied_date = fields.Datetime(string='Denied Date', readonly=True)
    deny_reason = fields.Text(string='Deny Reason')
    
    @api.depends('invoice_id', 'state')
    def _compute_installment_payment_link(self):
        """Get the collection.installment.payment record linked to this invoice"""
        for record in self:
            payment = False
            if record.invoice_id:
                payment = self.env['collection.installment.payment'].search([
                    ('invoice_id', '=', record.invoice_id.id)
                ], limit=1)
            record.installment_payment_id = payment
    
    @api.model
    def _populate_approved_receipt_if_empty(self):
        """Populate approved_receipt for approved records that don't have it"""
        approved_records = self.search([
            ('state', '=', 'approved'),
            '|', ('approved_receipt', '=', False), ('approved_receipt', '=', None)
        ])
        for record in approved_records:
            # Try to get payment from invoice_id
            payment = False
            if record.invoice_id:
                payment = self.env['collection.installment.payment'].search([
                    ('invoice_id', '=', record.invoice_id.id)
                ], limit=1)
            
            # Fallback to installment_payment_id
            if not payment and record.installment_payment_id:
                payment = record.installment_payment_id
            
            # Get receipt from payment or use original receipt
            receipt_data = False
            if payment and payment.payment_receipt:
                receipt_data = payment.payment_receipt
            elif record.payment_receipt:
                receipt_data = record.payment_receipt
            
            if receipt_data:
                record.approved_receipt = receipt_data
    
    @api.depends('invoice_id', 'state', 'payment_receipt', 'installment_payment_id')
    def _compute_approved_fields(self):
        """Fetch fields from collection.installment.payment for approved payments"""
        for record in self:
            if record.state == 'approved':
                # Try to get payment from invoice_id first (more reliable)
                payment = False
                if record.invoice_id:
                    payment = self.env['collection.installment.payment'].search([
                        ('invoice_id', '=', record.invoice_id.id)
                    ], limit=1)
                
                # Fallback to installment_payment_id if invoice lookup didn't work
                if not payment and record.installment_payment_id:
                    payment = record.installment_payment_id
                
                if payment:
                    record.approved_bank_id = payment.bank_id
                    record.approved_reference_number = payment.reference_number
                else:
                    # No payment found, use original values
                    record.approved_bank_id = record.bank_id
                    record.approved_reference_number = record.reference_number if record.reference_number else record.reference
            else:
                record.approved_bank_id = record.bank_id
                record.approved_reference_number = record.reference_number if record.reference_number else record.reference
    
    @api.depends('payment_receipt', 'approved_receipt', 'state')
    def _compute_receipt_display(self):
        """Compute field to show correct receipt based on state"""
        for record in self:
            if record.state == 'approved' and record.approved_receipt:
                record.receipt_display = record.approved_receipt
            else:
                record.receipt_display = record.payment_receipt
    
    def do_bulk_approve(self):
        """Bulk approve multiple draft payments"""
        if not self:
            raise UserError(_('Please select at least one payment to approve.'))
        draft_payments = self.filtered(lambda p: p.state == 'draft')
        if not draft_payments:
            raise UserError(_('Selected payments must be in draft state to approve.'))
        draft_payments.do_approve_payment()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Incoming Payment'),
            'res_model': 'payment.approval.record',
            'view_mode': 'tree',
            'domain': [],
            'context': {'search_default_draft': 1},
            'target': 'current',
        }

    @api.model
    def default_get(self, fields_list):
        """Override to populate approved_receipt for existing approved records"""
        res = super().default_get(fields_list)
        return res
    
    def do_approve_payment(self):
        """Approve the payment record and create/post invoice - FRESH IMPLEMENTATION"""
        # First, populate approved_receipt for any existing approved records that need it
        self._populate_approved_receipt_if_empty()
        
        for record in self.filtered(lambda p: p.state == 'draft'):
            if record.state != 'draft':
                raise UserError(_('Only draft payments can be approved.'))
            
            if not record.installment_id:
                raise UserError(_('Installment is required.'))
            
            # Step 1: Create payment record with status 'pending'
            payment_record = self.env['collection.installment.payment'].create({
                'installment_id': record.installment_id.id,
                'amount': record.amount,
                'payment_date': record.payment_date,
                'journal_type': record.journal_type,
                'reference': record.reference or '',
                'status': 'pending',
                'bank_id': record.bank_id.id if record.bank_id else False,
                'document_type_id': record.document_type_id.id if record.document_type_id else False,
                'payment_receipt': record.payment_receipt,
                'reference_number': record.reference_number or '',
            })
            # Invalidate installment payment_ids to ensure pending payment is recognized
            record.installment_id.invalidate_recordset(['payment_ids'])

            # Step 2: Apply Discount if any
            if record.apply_discount and record.discount_amount > 0:
                record.installment_id.write({
                    'discount_amount': record.installment_id.discount_amount + record.discount_amount
                })
                record.installment_id.collection_id.message_post(
                    body=f"Discount of {record.discount_percentage}% ({record.discount_amount}) applied to installment '{record.installment_id.name}' during payment."
                )

            # Step 3: Get income account
            income_account = self.env['account.account'].search([
                ('internal_group', '=', 'income'),
                ('deprecated', '=', False),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if not income_account:
                raise UserError(_("No income account found. Please configure one in Chart of Accounts."))

            # Step 4: Get site
            site_record = record.installment_id.site_id if record.installment_id else False
            
            # Step 5: Create invoice (EXACT match to collection wizard)
            invoice_data = {
                'move_type': 'out_invoice',
                'partner_id': record.installment_id.collection_id.partner_id.id,
                'invoice_date': record.payment_date,
                'invoice_origin': f'Payment {payment_record.reference or payment_record.id}',
                'is_collection_invoice': True,
                'company_id': self.env.company.id,
                'currency_id': record.installment_id.currency_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': f'Payment for {record.installment_id.name}',
                    'quantity': 1,
                    'price_unit': record.amount,
                    'account_id': income_account.id,
                })],
            }
            invoice_record = self.env['account.move'].create(invoice_data)
            
            # Set additional fields after creation (if they exist)
            if hasattr(invoice_record, 'payment_attachment') and record.attachment:
                invoice_record.write({'payment_attachment': record.attachment})
            if hasattr(invoice_record, 'payment_attachment_filename') and record.attachment_filename:
                invoice_record.write({'payment_attachment_filename': record.attachment_filename})
            if hasattr(invoice_record, 'payment_site_id') and site_record:
                invoice_record.write({'payment_site_id': site_record.id})

            # Step 6: Set FS Number (EXACT match to collection wizard)
            if record.reference_number:
                invoice_record.fs_number = record.reference
            else:
                invoice_record.fs_number = f"LEGACY-{payment_record.id}"

            # Step 7: Post Invoice (EXACT match to collection wizard)
            invoice_record.action_post()
            
            # Verify invoice was posted - force if needed
            invoice_record.invalidate_recordset(['state'])
            invoice_record = self.env['account.move'].browse(invoice_record.id)
            if invoice_record.state != 'posted':
                _logger.warning(f"Invoice {invoice_record.name} not posted, state: {invoice_record.state}. Forcing...")
                self.env.cr.execute("UPDATE account_move SET state = 'posted' WHERE id = %s", (invoice_record.id,))
                invoice_record.invalidate_recordset(['state'])
                invoice_record = self.env['account.move'].browse(invoice_record.id)

            # Step 8: Register Payment
            journal_type_map = {'cash': 'cash', 'bank': 'bank', 'check': 'bank'}
            journal_type = journal_type_map.get(record.journal_type, 'bank')
            journal_record = self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if journal_record:
                payment_register = self.env['account.payment.register'].with_context(
                    active_model='account.move',
                    active_ids=invoice_record.ids,
                ).create({
                    'journal_id': journal_record.id,
                    'amount': record.amount,
                    'payment_date': record.payment_date,
                })
                payment_register.action_create_payments()

            # Step 9: Link invoice to payment
            payment_record.invoice_id = invoice_record.id

            # Step 10: Update installment state (force recomputation)
            record.installment_id._compute_amount_paid()
            record.installment_id._compute_residual()
            record.installment_id._compute_state()
            # Invalidate to ensure UI updates
            record.installment_id.invalidate_recordset(['state'])

            # Step 11: Update reference_number from payment if it exists
            if payment_record.reference_number:
                record.reference_number = payment_record.reference_number
            elif payment_record.reference:
                record.reference_number = payment_record.reference

            # Step 12: Update record state to approved and copy receipt data
            # Get the receipt to store it (needed for binary_preview widget to work)
            receipt_data = False
            if payment_record.payment_receipt:
                receipt_data = payment_record.payment_receipt
            elif record.payment_receipt:
                receipt_data = record.payment_receipt
            
            record.write({
                'state': 'approved',
                'invoice_id': invoice_record.id,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'approved_receipt': receipt_data,  # Store the receipt directly (needed for binary_preview widget)
            })
            
            # Force recomputation of other approved fields (bank, reference)
            record._compute_approved_fields()
            
            record.message_post(body=_('Payment approved and invoice created: %s') % invoice_record.name)
        
        return True

    def do_bulk_deny(self):
        """Bulk deny multiple draft payments"""
        if not self:
            raise UserError(_('Please select at least one payment to deny.'))
        draft_payments = self.filtered(lambda p: p.state == 'draft')
        if not draft_payments:
            raise UserError(_('Selected payments must be in draft state to deny.'))
        
        return {
            'name': _('Deny Payment(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.deny.handler',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_record_ids': draft_payments.ids,
                'default_payment_record_id': draft_payments[0].id if len(draft_payments) == 1 else False,
                'bulk_mode': len(draft_payments) > 1,
            }
        }

    def do_deny(self):
        """Deny the payment record"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft payments can be denied.'))
        
        return {
            'name': _('Deny Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.deny.handler',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_record_id': self.id,
            }
        }
    
    def do_deny_confirm(self, reason=''):
        """Confirm denial of payment"""
        for record in self:
            if record.state != 'draft':
                continue
            installment = record.installment_id
            record.write({
                'state': 'denied',
                'denied_by': self.env.user.id,
                'denied_date': fields.Datetime.now(),
                'deny_reason': reason,
            })
            record.message_post(body=_('Payment denied. Reason: %s') % (reason or 'No reason provided'))
            # Trigger recomputation of installment state
            if installment:
                installment.invalidate_recordset(['state'])
                installment._compute_state()
        return True
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger installment state recomputation"""
        records = super().create(vals_list)
        # Trigger recomputation for installments with new draft/denied payments
        installments = records.mapped('installment_id').filtered(lambda i: i)
        installments.invalidate_recordset(['state'])
        installments._compute_state()
        return records
    
    def write(self, vals):
        """Override write to trigger installment state recomputation when state changes"""
        installments_to_update = self.env['collection.installment']
        if 'state' in vals or 'installment_id' in vals:
            # Get installments that might be affected
            for record in self:
                # Current installment (will be updated if installment_id changes)
                if record.installment_id:
                    installments_to_update |= record.installment_id
                # New installment if changing installment_id
                if 'installment_id' in vals and vals['installment_id']:
                    new_installment = self.env['collection.installment'].browse(vals['installment_id'])
                    installments_to_update |= new_installment
        
        result = super().write(vals)
        
        # Trigger recomputation
        for installment in installments_to_update:
            installment.invalidate_recordset(['state'])
            installment._compute_state()
        
        return result

    def open_invoice_record(self):
        """Open the related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice: %s') % (self.invoice_id.name or ''),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
            'views': [(False, 'form')],
            'context': {
                'form_view_initial_mode': 'readonly' if self.invoice_id.state != 'draft' else 'edit',
                'active_id': self.invoice_id.id,
                'active_model': 'account.move',
            },
        }

