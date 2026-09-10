# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import imghdr
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class PropertyTransferPayment(models.Model):
    _name = 'property.transfer.payment'
    _description = 'Property Transfer Payment'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer(string='Sequence', default=1)
    # Relationships
    transfer_id = fields.Many2one(
        'property.reservation.transfer.history',
        string="Transfer",
        required=True,
        ondelete='cascade'
    )

    document_type_id = fields.Many2one(
        'bank.document.type',
        string="Document Type",
        required=True,
        tracking=True
    )
    bank_id = fields.Many2one(
        'bank.configuration',
        string="Bank",
        required=True,
        tracking=True
    )

    # Payment Details
    payment_line_id = fields.Integer(string="Payment Line ID")
    ref_number = fields.Char(
        string="Reference Number",
        required=True,
        tracking=True
    )

    transaction_date = fields.Date(
        string="Transaction Date",
        required=True,
        tracking=True
    )
    amount = fields.Float(
        string="Amount",
        tracking=True
    )
    amount_display = fields.Float(
        string="Display Amount",
        tracking=True,
    )

    # Documents
    payment_receipt = fields.Binary(
        string="Payment Receipt",
        required=True,
        tracking=True
    )

    # Control Fields
    id_editable = fields.Boolean(
        string="Is Editable",
        default=False
    )

    # _sql_constraints = [
    #     ('unique_ref_number',
    #      'unique(ref_number)',
    #      'The Reference Number must be unique.')
    # ]

    @api.constrains('ref_number')
    def validate_ref_number(self):
        for rec in self:
            payments = self.env['property.transfer.payment'].search([
                ('id', '!=', rec.id),
                ('ref_number', '=', rec.ref_number),
                ('transfer_id.status', 'not in', ['rejected'])
            ])
            if payments:
                raise ValidationError(_("The Reference Number must be unique."))

    @api.model
    def create(self, vals):
        """Create transfer payment with validation."""
        if isinstance(vals, list):
            for val in vals:
                if not val.get('document_type_id'):
                    payment = self._get_payment_details(val.get('payment_line_id'))
                    self._update_payment_vals(val, payment)
        return super().create(vals)

    def _get_payment_details(self, payment_id):
        """Get payment details from reservation payment."""
        return self.env['property.reservation.payment'].browse(payment_id)

    def _update_payment_vals(self, val, payment):
        """Update payment values from existing payment."""
        if payment:
            val.update({
                'payment_receipt': payment.payment_receipt,
                'document_type_id': payment.document_type_id.id,
                'bank_id': payment.bank_id.id,
                'ref_number': payment.ref_number,
                'transaction_date': payment.transaction_date,
                'amount': payment.amount
            })

    @api.constrains('payment_receipt')
    def _check_file_type(self):
        """Validate payment receipt file type."""
        allowed_image_types = ['jpeg', 'png', 'gif']
        pdf_signature = b'%PDF'

        for record in self:
            if not record.payment_receipt:
                continue

            file_data = base64.b64decode(record.payment_receipt)
            
            # Check PDF
            if file_data.startswith(pdf_signature):
                continue
                
            # Check Images
            image_type = imghdr.what(None, file_data)
            if image_type not in allowed_image_types:
                raise ValidationError(_(
                    "Only PDF and image files (JPEG, PNG, GIF) are allowed for Payment Receipt."
                ))

    @api.constrains('amount', 'amount_display')
    def _validate_amounts(self):
        """Validate payment amounts."""
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero"))
            # if record.amount_display <= 0:
            #     raise ValidationError(_("Display amount must be greater than zero"))

    @api.constrains('transaction_date')
    def _validate_transaction_date(self):
        """Validate transaction date."""
        for record in self:
            if record.transaction_date > fields.Date.today():
                raise ValidationError(_("Transaction date cannot be in the future"))
            

class PropertyReservationTransfer(models.Model):
    _name = 'property.reservation.transfer.history'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Property Reservation Transfer History'
    _rec_name = 'reservation_id'
    _order = 'create_date desc'

    # Relationships
    reservation_id = fields.Many2one(
        'property.reservation',
        string="Reservation",
        required=True,
        tracking=True
    )

    reservation_id2 = fields.Many2one(
        'property.reservation',
        string="Reservation",
    )
    old_property_id = fields.Many2one(
        'property.property',
        string="Old Property",
    )
    property_id = fields.Many2one(
        'property.property',
        string="Transfer to Property",
        domain=[('state', '=', 'available')],
        required=True,
        tracking=True
    )
    payment_line_ids = fields.One2many(
        'property.transfer.payment',
        'transfer_id',
        string="Payment Lines"
    )

    # Status and Documents
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', tracking=True, default='draft')
    request_letter = fields.Binary(
        string="Request Letter",
        required=True,
        tracking=True
    )

    # Computed Fields
    total_paid = fields.Float(
        string="Total Paid",
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )
    is_sufficient = fields.Boolean('Is Sufficient', compute='_compute_total_amount', store=True)
    payment_diff = fields.Float('Difference', compute='_compute_total_amount')
    expected_amount = fields.Float('Expected Amount', compute='_compute_total_amount')


    @api.depends('payment_line_ids', 'reservation_id', 'property_id')
    def _compute_total_amount(self):
        """Compute total amount from payment lines."""
        for rec in self:
            rec.total_paid = sum(rec.payment_line_ids.mapped('amount'))
            if rec.reservation_id.reservation_type_id.is_payment_required:
                total = sum(rec.payment_line_ids.mapped('amount'))
                expected = rec.compute_expected_amount()
                discount = rec.compute_discount_amount()
                expected = expected - (expected * discount)
                rec.expected_amount = expected
                rec.is_sufficient = total >= expected
                rec.payment_diff = expected - total
            else:
                rec.expected_amount = 0
                rec.payment_diff = 0
                rec.is_sufficient = True

    def compute_expected_amount(self):
        """Calculate the expected payment amount based on payment type."""
        self.ensure_one()
        if self.reservation_id.reservation_type_id.payment_type == "fixed":
            return self.reservation_id.reservation_type_id.amount

        # Calculate percentage-based amount
        if self.property_id.is_multi:
            payment_term_line = self.env['property.payment.term.line'].search(
                [('id', '=', self.property_id.site_payment_structure_id.payment_term_id.id)],
                order='sequence', limit=1)
        else:
            payment_term_line = self.env['property.payment.term.line'].search(
                [('id', '=', self.property_id.payment_structure_id.id)],
                order='sequence', limit=1)

        expected_per = payment_term_line.percentage if payment_term_line else 0
        base_amount = (self.property_id.unit_price
                       if self.property_id.sale_rent == "for_sale"
                       else self.property_id.rent_month)

        return (base_amount * expected_per / 100) * (self.reservation_id.reservation_type_id.amount / 100)

    def compute_discount_amount(self):
        for rec in self:
            total = 0.0
            discounts = self.env['property.special.discount'].search([
                ('partner_id', '=', rec.reservation_id.partner_id.id),
                ('property_id', '=', rec.property_id.id),
                ('status', '=', 'approved')
            ])
            for dis in discounts:
                total += dis.discount

            return total



    @api.model
    def create(self, vals):
        reservation = self.env['property.reservation'].browse(vals.get('reservation_id'))
        payment_lines = vals.get('payment_line_ids', [])
        total_amount1 = 0.0
        filtered_lines=[]
        for command in payment_lines:
            if command[0] in [0, 1]:  # Create or update record
                line_data = command[2]
                if line_data.get('id_editable') is False:
                    total_amount1 += command[2].get('amount', 0.0)
                    filtered_lines.append((0, 0, {
                        'payment_line_id': command[2].get('id'),
                        'document_type_id': command[2].get('document_type_id'),
                        'bank_id': command[2].get('bank_id'),
                        'ref_number': command[2].get('ref_number'),
                        'transaction_date':command[2].get('transaction_date'),
                        'amount': command[2].get('amount'),
                        'amount_display': command[2].get('amount'),
                        'payment_receipt': command[2].get('payment_receipt'),
                        'id_editable': False,
                    }))

        if not reservation:
            raise ValidationError(_("Invalid reservation reference"))
        total_amount=sum(line_p.amount for line_p in reservation.payment_line_ids)
        total_amount1=total_amount1+total_amount

        # Validate transfer
        self._validate_transfer(reservation, total_amount1, vals.get('property_id'))

        # Update reservation status
        reservation.sudo().write({'transfer_status': 'pending'})
        payment_line_vals = []
        for payment in reservation.payment_line_ids:
            filtered_lines.append((0, 0, {
                'payment_line_id': payment.id,
                'document_type_id': payment.document_type_id.id,
                'bank_id': payment.bank_id.id,
                'ref_number': payment.ref_number,
                'transaction_date': payment.transaction_date,
                'amount': payment.amount,
                'amount_display': payment.amount,
                'payment_receipt': payment.payment_receipt,
                'id_editable': True,
            }))
        # Update vals with payment lines
        vals.update({
            'status': 'pending',
            'old_property_id': reservation.property_id.id,
            'payment_line_ids': filtered_lines
        })

        return super().create(vals)

    def approve_transfer(self):
        """Approve transfer request."""
        self.ensure_one()
        if self.status != 'pending':
            raise ValidationError(_("Only pending transfers can be approved"))

        if self.property_id.state != 'available':
            raise ValidationError(_(
                "Cannot approve transfer. Property %s is not available (current state: %s)"
            ) % (self.property_id.name, self.property_id.state))

        # Update property states
        self.property_id.sudo().write({'state': 'reserved'})
        self.old_property_id.sudo().write({'state': 'available'})

        # Update reservation
        self.reservation_id.sudo().write({
            'property_id': self.property_id.id,
            'transfer_status': 'approved'
        })

        # Create payment records
        self._create_payment_records()

        self.status = 'approved'
        channel = self.env['discuss.channel'].search([('name', '=', 'general')], limit=1)
        expire_date = self.reservation_id.expire_date + timedelta(hours=3)
        if channel:
            channel.message_post(
                body=(f"Property {self.reservation_id.property_id.name} is reserved, reservation will expire on {expire_date}"),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    def reject_transfer(self):
        """Reject transfer request."""
        self.ensure_one()
        if self.status != 'pending':
            raise ValidationError(_("Only pending transfers can be rejected"))

        self.reservation_id.sudo().write({'transfer_status': 'rejected'})
        self.status = 'rejected'

    def transfer_request_detail(self):
        """Show transfer request details."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Request'),
            'res_model': self._name,
            'view_mode': 'form,tree',
            'target': 'current',
            'res_id': self.id,
        }

    def _validate_transfer(self, reservation, total_amount, property_id):
        """Validate transfer request."""
        if not reservation.reservation_type_id.is_payment_required:
            return

        expected = self._compute_expected_amount(reservation, property_id)
        if total_amount < expected:
            raise ValidationError(_(
                "Insufficient amount. Expected amount is %s"
            ) % expected)

    def _compute_expected_amount(self, reservation, property_id):
        """Compute expected amount for transfer."""
        property = self.env['property.property'].browse(property_id)
        if not property:
            raise ValidationError(_("Invalid property reference"))

        if reservation.reservation_type_id.payment_type == "fixed":
            return reservation.amount

        # Get payment term line
        payment_term_line = self._get_payment_term_line(property)
        if not payment_term_line:
            return 0

        # Calculate expected amount
        base_amount = (
            property.unit_price if property.sale_rent == "for_sale"
            else property.rent_month
        )
        return (
            base_amount * 
            payment_term_line.percentage / 100 * 
            reservation.reservation_type_id.amount / 100
        )

    def _get_payment_term_line(self, property):
        """Get payment term line based on property type."""
        domain = [
            ('id', '=', 
             property.site_payment_structure_id.payment_term_id.id
             if property.is_multi
             else property.payment_structure_id.id)
        ]
        return self.env['property.payment.term.line'].search(
            domain, order='sequence', limit=1
        )

    def _create_payment_records(self):
        filtered_payment_lines = self.payment_line_ids.filtered(
            lambda l: l.id_editable !=  True
        )
        payment_vals = [
            {
                'reservation_id': self.reservation_id.id,
                'payment_receipt': line.payment_receipt,
                'document_type_id': line.document_type_id.id,
                'bank_id': line.bank_id.id,
                'ref_number': line.ref_number,
                'transaction_date': line.transaction_date,
                'amount': line.amount,
            }
            for line in filtered_payment_lines
        ]
        if payment_vals:
            self.env['property.reservation.payment'].create(payment_vals)