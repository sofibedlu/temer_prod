from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyReservationPayment(models.Model):
    _inherit = 'property.reservation.payment'

    pre_contract_refunded = fields.Boolean(
        string='Pre-Contract Refunded',
        default=False,
        copy=False,
        tracking=True,
        help='Checked after this payment is included in a paid pre-contract refund.',
    )
    pre_contract_refund_id = fields.Many2one(
        'property.pre.contract.refund',
        string='Pre-Contract Refund',
        readonly=True,
        copy=False,
    )

    def _format_pre_contract_refund_display_name(self):
        self.ensure_one()
        parts = [
            self.ref_number,
            self.document_type_id.display_name,
            str(self.amount) if self.amount else False,
        ]
        return ' / '.join(filter(None, parts)) or _('Reservation Payment %s') % self.id

    @api.depends('ref_number', 'document_type_id', 'amount')
    def _compute_display_name(self):
        super()._compute_display_name()
        for payment in self:
            payment.display_name = payment._format_pre_contract_refund_display_name()

    def name_get(self):
        if not self.env.context.get('pre_contract_refund_payment_selection'):
            return super().name_get()

        return [(payment.id, payment._format_pre_contract_refund_display_name()) for payment in self]


class PropertyPreContractRefundBankLine(models.Model):
    _name = 'property.pre.contract.refund.bank.line'
    _description = 'Pre Contract Refund Bank Line'
    _order = 'id'

    refund_id = fields.Many2one(
        'property.pre.contract.refund',
        string='Refund',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='refund_id.partner_id',
        store=True,
        readonly=True,
    )
    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        related='refund_id.reservation_id',
        store=True,
        readonly=True,
    )
    refund_type_code = fields.Selection(
        related='refund_id.refund_type_code',
        string='Refund Type Code',
        readonly=True,
    )
    payment_line_id = fields.Many2one(
        'property.reservation.payment',
        string='Reservation Payment',
        domain="[('reservation_id', '=', reservation_id), ('payment_status', '!=', 'canceled'), ('pre_contract_refunded', '=', False)]",
        ondelete='restrict',
    )
    payment_ref_number = fields.Char(
        string='Payment Reference',
        related='payment_line_id.ref_number',
        store=True,
        readonly=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        related='payment_line_id.transaction_date',
        store=True,
        readonly=True,
    )
    payment_document_type_id = fields.Many2one(
        'bank.document.type',
        string='Payment Document Type',
        related='payment_line_id.document_type_id',
        store=True,
        readonly=True,
    )
    payment_bank_id = fields.Many2one(
        'bank.configuration',
        string='Payment Bank',
        related='payment_line_id.bank_id',
        store=True,
        readonly=True,
    )
    payment_amount = fields.Float(
        string='Payment Amount',
        related='payment_line_id.amount',
        store=True,
        readonly=True,
    )
    bank_id = fields.Many2one(
        'property.customer.bank',
        string='Bank Name',
        ondelete='restrict',
    )
    bank_name = fields.Char(
        string='Bank Name',
        related='bank_id.bank_name',
        store=True,
        readonly=True,
    )
    account_detail_id = fields.Many2one(
        'property.customer.bank.detail',
        string='Account Number',
        domain="[('partner_id', '=', partner_id), ('bank_name', '=', bank_name)]",
        ondelete='restrict',
    )
    account_number = fields.Char(
        string='Account Number',
        related='account_detail_id.account_number',
        store=True,
        readonly=True,
    )
    account_holder = fields.Char(
        string='Account Holder',
        help='Account holder name as stated on the application letter.',
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='refund_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        self.account_detail_id = False

    @api.constrains('bank_id', 'account_detail_id', 'account_holder', 'amount', 'payment_line_id')
    def _check_line(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_('Refund amount per bank line must be greater than zero.'))
            if line.refund_type_code == 'overpayment' and not line.payment_line_id:
                raise ValidationError(_('Please select the reservation payment to deduct from.'))
            if line.payment_line_id and line.payment_line_id.pre_contract_refunded:
                raise ValidationError(_('This reservation payment was already refunded.'))
            if not line.bank_id:
                raise ValidationError(_('Please select or create a bank on each line.'))
            if not line.account_detail_id:
                raise ValidationError(_('Please select or create an account number on each line.'))
            if not (line.account_holder or '').strip():
                raise ValidationError(_('Please enter the account holder on each bank line.'))
