from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from ..models.access_control import require_feature

class PropertyPaymentRegisterWizard(models.TransientModel):
    _name = 'property.payment.register.wizard'
    _description = 'Register Payment Wizard'

    installment_id = fields.Many2one('collection.installment', string='Installment', required=True, readonly=True)
    currency_id = fields.Many2one(related='installment_id.currency_id')
    
    amount = fields.Monetary(string='Payment Amount', required=True)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today, required=True)
    apply_discount = fields.Boolean(string="Apply Discount", default=False)
    discount_percentage = fields.Float(string="Discount (%)")
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id', help="Calculated discount amount.")

    journal_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check')
    ], string='Payment Method', default='bank', required=True)
    reference = fields.Char(string='Reference')

    bank_id = fields.Many2one('bank.configuration', string="Bank")
    document_type_id = fields.Many2one('bank.document.type', string="Document Type")
    payment_receipt = fields.Binary(string="Payment Receipt")
    reference_number = fields.Char(string="Reference Number")

    def _get_default_can_apply_discount(self):
        return self.env.user.has_group("collection_management.group_collection_manager")
    can_apply_discount = fields.Boolean(
        default=_get_default_can_apply_discount, 
        store=False
    )

    @api.onchange('apply_discount', 'discount_percentage')
    def _onchange_discount_details(self):
        """
        Automatically calculate discount amount and update payment amount
        """
        if not self.installment_id:
            return

        residual = self.installment_id.amount_residual
        
        if self.apply_discount:
            calculated_discount = residual * (self.discount_percentage / 100.0)
            self.discount_amount = calculated_discount
            self.amount = residual - calculated_discount
        else:
            # Reset if unchecked
            self.discount_amount = 0.0
            self.discount_percentage = 0.0
            self.amount = residual

    def action_confirm_payment(self):
        require_feature(self.env, "payment_initiate", message="You are not allowed to confirm payments.")
        # Check Manual Discount Limit
        if self.apply_discount and self.discount_percentage > 0:
            config = self.env['collection.discount.config'].sudo().search([], limit=1)
            max_percent = config.max_manual_discount_percentage if config else 10.0
            
            if self.discount_percentage > max_percent:
                 raise UserError(_("You cannot apply a discount of %s%%. The maximum allowed is %s%%.") % (self.discount_percentage, max_percent))
            
        # Create the payment record with status 'pending'
        payment = self.env['collection.installment.payment'].sudo().create({
            'installment_id': self.installment_id.id,
            'amount': self.amount,
            'payment_date': self.payment_date,
            'journal_type': self.journal_type,
            'reference': self.reference,
            'status': 'pending',

            'bank_id': self.bank_id.id,
            'document_type_id': self.document_type_id.id,
            'payment_receipt': self.payment_receipt,
            'reference_number': self.reference_number,
        })

        # Apply Discount to the Installment
        if self.apply_discount and self.discount_amount > 0:
            self.installment_id.sudo().write({
                'discount_amount': self.installment_id.discount_amount + self.discount_amount
            })
            
            self.installment_id.collection_id.sudo().message_post(
                body=f"Discount of {self.discount_percentage}% ({self.discount_amount}) applied to installment '{self.installment_id.name}' during payment."
            )

        # Create a draft invoice for this payment
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.installment_id.collection_id.partner_id.id,
            'invoice_date': self.payment_date,
            'invoice_origin': f'Payment {payment.reference or payment.id}',
            'is_collection_invoice': True, # Mark as collection invoice
            'company_id': self.env.company.id,
            'currency_id': self.installment_id.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': f'Payment for {self.installment_id.name}',
                'quantity': 1,
                'price_unit': self.amount,
                'account_id': self._get_income_account().id,
            })],
        }
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # ========================================================
        # TEMPORARY FOR LEGACY DATA: Post Invoice & Register Payment
        # default
        #payment.invoice_id = invoice.id  # Link the invoice to the payment
        
        # 1. Set FS Number
        if self.reference:
            invoice.fs_number = self.reference
        else:
            invoice.fs_number = f"LEGACY-{payment.id}"

        # 2. Post Invoice
        invoice.action_post()

        # 3. Register Payment
        journal_type_map = {'cash': 'cash', 'bank': 'bank', 'check': 'bank'}
        j_type = journal_type_map.get(self.journal_type, 'bank')
        journal = self.env['account.journal'].search([
            ('type', '=', j_type),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if journal:
            payment_register = self.env['account.payment.register'].sudo().with_context(
                active_model='account.move',
                active_ids=invoice.ids,
            ).create({
                'journal_id': journal.id,
                'amount': self.amount,
                'payment_date': self.payment_date,
            })
            payment_register.action_create_payments()

        payment.invoice_id = invoice.id
        # ========================================================


        # Trigger compute methods to update installment state
        self.installment_id.sudo()._compute_amount_paid()
        self.installment_id.sudo()._compute_residual()
        self.installment_id.sudo()._compute_state()

        return {'type': 'ir.actions.act_window_close'}

    def _get_income_account(self):
        """Helper to get a default income account."""
        account = self.env['account.account'].sudo().search([
            ('internal_group', '=', 'income'),
            ('deprecated', '=', False),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not account:
            raise UserError("No income account found. Please configure one in Chart of Accounts.")
        return account