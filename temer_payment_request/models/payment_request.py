# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


PERMISSION_ERROR = _("You don't have permission to perform this action.")


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _description = 'Payment Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'pr_number desc'
    _rec_name = 'pr_number'
    _check_company_auto = True

    pr_number = fields.Char(
        string='PR Number',
        required=True, readonly=True, index=True,
        default=lambda self: _('New'), copy=False,
    )
    pay_to = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
    ], string='Pay To', required=True, tracking=True, default='customer')
    partner_id = fields.Many2one(
        'res.partner',
        string='Payee Name',
        required=True,
        tracking=True,
        context={'default_supplier_rank': 1, 'res_partner_search_mode': 'supplier'},
        domain="['|', ('supplier_rank', '>', 0), ('customer_rank', '>', 0)]",
    )
    reason = fields.Text(string='Reason for Payment', required=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.ETB').id, required=True,
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
        ('void', 'Void'),
    ], string='Status', default='draft', tracking=True, readonly=True)
    created_by = fields.Many2one('res.users', string='Created By',
        default=lambda self: self.env.user, readonly=True)
    checked_by = fields.Many2one('res.users', string='Checked By', readonly=True)
    checked_date = fields.Datetime(string='Checked Date', readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    voided_by = fields.Many2one('res.users', string='Voided By', readonly=True)
    voided_date = fields.Datetime(string='Voided Date', readonly=True)
    void_reason = fields.Text(string='Void Reason')
    payment_order_id = fields.Many2one('payment.order', string='Payment Order',
        readonly=True, copy=False)

    _sql_constraints = [
        ('pr_number_unique', 'unique(pr_number, company_id)', 'PR Number must be unique per company!'),
    ]

    VALID_TRANSITIONS = {
        'draft': ['checked', 'canceled'],
        'checked': ['approved', 'draft', 'canceled'],
        'approved': ['done', 'canceled', 'void'],
        'done': ['canceled'],
        'canceled': [],
        'void': [],
    }

    # @api.constrains('partner_id', 'pay_to')
    # def _check_partner_type(self):
    #     for rec in self:
    #         if rec.pay_to == 'vendor' and not rec.partner_id.supplier_rank:
    #             raise UserError(_('Selected partner must be a vendor (have supplier rank).'))
    #         if rec.pay_to == 'customer' and not rec.partner_id.customer_rank:
    #             raise UserError(_('Selected partner must be a customer (have customer rank).'))

    @api.depends('pr_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.pr_number

    def _is_creator(self):
        return self.env.user.has_group('temer_payment_request.group_payment_request_creator')

    def _is_checker(self):
        return self.env.user.has_group('temer_payment_request.group_payment_request_checker')

    def _is_approver(self):
        return self.env.user.has_group('temer_payment_request.group_payment_request_approver')

    def _is_manager(self):
        return self.env.user.has_group('temer_payment_request.group_payment_request_manager')

    def _is_own_record(self):
        self.ensure_one()
        return self.created_by.id == self.env.user.id

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('temer_payment_request.group_payment_request_creator'):
            raise UserError(PERMISSION_ERROR)

        for vals in vals_list:
            if vals.get('pr_number', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('payment.request')
                if not seq or seq == _('New'):
                    raise UserError(_('Failed to generate PR Number. Please check the sequence configuration.'))
                vals['pr_number'] = seq
        return super(PaymentRequest, self).create(vals_list)

    def action_check(self):
        if not self.env.user.has_group('temer_payment_request.group_payment_request_checker'):
            raise UserError(PERMISSION_ERROR)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft payment requests can be checked.'))
            if float_compare(rec.amount, 0.0, precision_rounding=rec.currency_id.rounding) <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec.write({
                'state': 'checked',
                'checked_by': self.env.user.id,
                'checked_date': fields.Datetime.now(),
            })
            rec.message_post(body=_('Payment Request checked by %s') % self.env.user.name)

    def action_approve(self):
        if not self.env.user.has_group('temer_payment_request.group_payment_request_approver'):
            raise UserError(PERMISSION_ERROR)
        for rec in self:
            if rec.state != 'checked':
                raise UserError(_('Only checked payment requests can be approved.'))
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            rec.message_post(body=_('Payment Request approved by %s') % self.env.user.name)
            rec._create_payment_order()

    def action_void(self):
        if not self.env.user.has_group('temer_payment_request.group_payment_request_manager'):
            raise UserError(PERMISSION_ERROR)
        for rec in self:
            if rec.state in ('done', 'void', 'canceled'):
                raise UserError(_('Cannot void a done, canceled, or already void payment request.'))
            if rec.payment_order_id:
                raise UserError(_('Cannot void a payment request with an existing payment order. Cancel the PO first.'))
            if not rec.void_reason or not rec.void_reason.strip():
                raise UserError(_('Please provide a void reason before voiding.'))
            rec.write({
                'state': 'void',
                'voided_by': self.env.user.id,
                'voided_date': fields.Datetime.now(),
            })
            rec.message_post(body=_('Payment Request voided by %s - Reason: %s') % (self.env.user.name, rec.void_reason))

    def action_reset_to_draft(self):
        if not self.env.user.has_group('temer_payment_request.group_payment_request_checker'):
            raise UserError(PERMISSION_ERROR)
        for rec in self:
            if rec.state != 'checked':
                raise UserError(_('Only checked payment requests can be reset to draft.'))
            if rec.payment_order_id:
                raise UserError(_('Cannot reset: a Payment Order already exists. Cancel the PO first.'))
            rec.write({
                'state': 'draft',
                'checked_by': False,
                'checked_date': False,
            })
            rec.message_post(body=_('Payment Request reset to draft by %s') % self.env.user.name)

    def _create_payment_order(self):
        self.ensure_one()
        if self.payment_order_id:
            raise UserError(_('Payment Order already exists for this request.'))
        po = self.env['payment.order'].with_context(
            from_payment_request=True,
            company_id=self.company_id.id,
        ).sudo().create({
            'pr_number': self.pr_number,
            'pay_to': self.pay_to,
            'partner_id': self.partner_id.id,
            'reason': self.reason,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_request_id': self.id,
            'company_id': self.company_id.id,
        })
        self.payment_order_id = po.id

    def write(self, vals):
        if 'state' in vals:
            new_state = vals['state']
            for rec in self:
                if new_state not in self.VALID_TRANSITIONS.get(rec.state, []):
                    raise UserError(_('Invalid state transition from %s to %s') % (rec.state, new_state))
                if new_state == 'checked':
                    if not self.env.user.has_group('temer_payment_request.group_payment_request_checker'):
                        raise UserError(PERMISSION_ERROR)
                elif new_state == 'approved':
                    if not self.env.user.has_group('temer_payment_request.group_payment_request_approver'):
                        raise UserError(PERMISSION_ERROR)
                elif new_state == 'done':
                    if not self.env.user.has_group('temer_payment_request.group_payment_order_confirmer'):
                        raise UserError(PERMISSION_ERROR)
                elif new_state == 'canceled':
                    if not self.env.user.has_group('temer_payment_request.group_payment_order_confirmer'):
                        raise UserError(PERMISSION_ERROR)
                elif new_state == 'void':
                    if not self.env.user.has_group('temer_payment_request.group_payment_request_manager'):
                        raise UserError(PERMISSION_ERROR)

        for rec in self:
            if rec.state == 'draft' and rec.id:
                allowed_fields = {'state', 'checked_by', 'checked_date', 'approved_by', 'approved_date', 'voided_by', 'voided_date', 'void_reason', 'payment_order_id', 'pay_to', 'partner_id', 'reason', 'amount', 'currency_id'}
                field_changes = set(vals.keys()) - allowed_fields
                if field_changes:
                    if not (rec._is_creator() and rec._is_own_record()) and not rec._is_checker():
                        raise UserError(PERMISSION_ERROR)

            if rec.state == 'checked':
                allowed_fields = {'state', 'checked_by', 'checked_date', 'approved_by', 'approved_date', 'voided_by', 'voided_date', 'void_reason', 'payment_order_id', 'pay_to', 'partner_id', 'reason', 'amount', 'currency_id'}
                if not set(vals.keys()) <= allowed_fields:
                    raise UserError(PERMISSION_ERROR)
                # FIX: Allow both checkers AND approvers to write when state is 'checked'
                if not rec._is_checker() and not rec._is_approver():
                    raise UserError(PERMISSION_ERROR)

            if rec.state in ('approved', 'done', 'canceled', 'void'):
                allowed_fields = {'state', 'checked_by', 'checked_date', 'approved_by', 'approved_date', 'voided_by', 'voided_date', 'void_reason', 'payment_order_id'}
                if not set(vals.keys()) <= allowed_fields:
                    raise UserError(PERMISSION_ERROR)

        return super(PaymentRequest, self).write(vals)

    def unlink(self):
        raise UserError(_('Payment Requests cannot be deleted.'))