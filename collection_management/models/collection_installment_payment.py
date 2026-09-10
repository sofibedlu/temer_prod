from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

class CollectionInstallmentPayment(models.Model):
    _name = 'collection.installment.payment'
    _description = 'Installment Payment'
    _order = 'payment_date desc, id desc'

    installment_id = fields.Many2one('collection.installment', string='Installment', ondelete='cascade', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='installment_id.currency_id', store=True)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today, required=True)
    journal_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check')
    ], string='Method', default='bank')
    reference = fields.Char(string='Reference')

    bank_id = fields.Many2one('bank.configuration', string="Bank")
    document_type_id = fields.Many2one('bank.document.type', string="Document Type")
    payment_receipt = fields.Binary(string="Payment Receipt")
    reference_number = fields.Char(string="Reference Number")
    
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid')
    ], string='Payment Status', compute='_compute_status_and_fs', store=True, tracking=True)
    fs_number = fields.Char(string='FS Number', compute='_compute_status_and_fs', store=True, help="Fetched from Invoice Reference")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for val in vals:
                self._validate_payment_amount(val)
        else:
            self._validate_payment_amount(vals)
        return super(CollectionInstallmentPayment, self).create(vals)

    def _validate_payment_amount(self, vals):
        """Validate amount is positive and does not exceed residual."""
        amount = vals.get('amount', 0)
        if amount <= 0:
            raise UserError(_("Payment amount must be greater than zero."))

        if vals.get('installment_id'):
            installment = self.env['collection.installment'].browse(vals['installment_id'])
            if float_compare(amount, installment.amount_residual, precision_digits=2) > 0:
                 raise UserError(_(
                     "You cannot pay %s. The remaining amount for this installment is only %s."
                 ) % (amount, installment.amount_residual))

    @api.depends('invoice_id.payment_state', 'invoice_id.fs_number')
    def _compute_status_and_fs(self):
        for rec in self:
            if rec.invoice_id:
                if rec.invoice_id.payment_state in ['paid', 'in_payment']:
                    rec.status = 'paid'
                else:
                    rec.status = 'pending'
                rec.fs_number = rec.invoice_id.fs_number
            else:
                if rec.status == 'paid':
                    rec.status = 'paid'
                else:
                    rec.status = 'pending'
