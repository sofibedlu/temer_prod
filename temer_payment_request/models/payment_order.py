# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PaymentOrder(models.Model):
    _name = 'payment.order'
    _description = 'Payment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'po_number desc'
    _rec_name = 'po_number'
    _check_company_auto = True

    po_number = fields.Char(
        string='PO Number', required=True, readonly=True, index=True,
        default=lambda self: _('New'), copy=False,
    )
    pr_number = fields.Char(string='PR Number', required=True, readonly=True)
    pay_to = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
    ], string='Pay To', required=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Payee Name',
        required=True,
        readonly=True,
    )
    payee_name = fields.Char(
        string='Payee Name (Display)',
        readonly=True,
    )
    reason = fields.Text(string='Reason', required=True, readonly=True)
    amount = fields.Monetary(string='Amount', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
    ], string='Status', default='draft', tracking=True, readonly=True)
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', readonly=True)
    confirmed_date = fields.Datetime(string='Confirmed Date', readonly=True)
    canceled_by = fields.Many2one('res.users', string='Canceled By', readonly=True)
    canceled_date = fields.Datetime(string='Canceled Date', readonly=True)
    cancel_reason = fields.Text(string='Cancellation Reason', readonly=True)
    payment_request_id = fields.Many2one('payment.request', string='Payment Request',
        readonly=True, ondelete='restrict', copy=False)
    account_payment_id = fields.Many2one('account.payment', string='Account Payment',
        readonly=True, copy=False, ondelete='set null')

    _sql_constraints = [
        ('po_number_unique', 'unique(po_number, company_id)', 'PO Number must be unique per company!'),
    ]

    @api.depends('po_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.po_number

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('from_payment_request'):
            raise UserError(_('Payment Orders can only be created from approved Payment Requests.'))
        for vals in vals_list:
            if vals.get('po_number', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('payment.order')
                if not seq or seq == _('New'):
                    raise UserError(_('Failed to generate PO Number. Please check the sequence configuration.'))
                vals['po_number'] = seq
            if vals.get('partner_id') and not vals.get('payee_name'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['payee_name'] = partner.name
        return super(PaymentOrder, self).create(vals_list)

    def write(self, vals):
        tracked_fields = {'partner_id', 'amount', 'reason', 'pay_to'}
        # Store old values BEFORE super().write() for proper change tracking
        old_values = {}
        for rec in self:
            if rec.state == 'draft':
                old_values[rec.id] = {
                    'partner_id': rec.partner_id.id,
                    'partner_name': rec.partner_id.name if rec.partner_id else _('None'),
                    'pay_to': rec.pay_to,
                    'amount': rec.amount,
                    'reason': rec.reason or '',
                }

        result = super(PaymentOrder, self).write(vals)

        for rec in self:
            if rec.state == 'draft' and rec.id in old_values:
                old = old_values[rec.id]
                changes = []

                if 'partner_id' in vals:
                    new_partner = self.env['res.partner'].browse(vals['partner_id']) if vals['partner_id'] else False
                    new_name = new_partner.name if new_partner else _('None')
                    if old['partner_name'] != new_name:
                        changes.append(_('Payee Name changed from "%s" to "%s"') % (old['partner_name'], new_name))

                if 'pay_to' in vals:
                    old_label = dict(rec._fields['pay_to'].selection).get(old['pay_to'], old['pay_to'])
                    new_label = dict(rec._fields['pay_to'].selection).get(vals['pay_to'], vals['pay_to'])
                    if old['pay_to'] != vals['pay_to']:
                        changes.append(_('Pay To changed from "%s" to "%s"') % (old_label, new_label))

                if 'amount' in vals:
                    if float_compare(old['amount'], vals['amount'], precision_rounding=rec.currency_id.rounding) != 0:
                        changes.append(_('Amount changed from %s to %s') % (old['amount'], vals['amount']))

                if 'reason' in vals:
                    new_reason = vals['reason'] or ''
                    if old['reason'] != new_reason:
                        changes.append(_('Reason changed from "%s" to "%s"') % (old['reason'], new_reason))

                if changes:
                    # Build message with bullet points using chr() to avoid literal special chars
                    nl = chr(10)
                    bullet = chr(8226) + ' '
                    bullet_changes = (nl + bullet).join(changes)
                    message_body = _('Payment Order edited by %s:') % self.env.user.name + nl + bullet + bullet_changes
                    # Post on the Payment Order itself
                    rec.sudo().message_post(body=message_body)
                    # Also post on the connected Payment Request (if any)
                    if rec.payment_request_id:
                        rec.payment_request_id.sudo().message_post(
                            body=_('Linked Payment Order %s was edited by %s:') % (rec.po_number, self.env.user.name) + nl + bullet + bullet_changes
                        )

        return result

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft payment orders can be confirmed.'))
            if rec.payment_request_id and rec.payment_request_id.state != 'approved':
                raise UserError(_('The related Payment Request must be approved before confirming.'))
            payment = rec._create_account_payment()
            rec.write({
                'state': 'confirmed',
                'confirmed_by': self.env.user.id,
                'confirmed_date': fields.Datetime.now(),
                'account_payment_id': payment.id,
            })
            # FIX: Use sudo() to update the linked Payment Request state
            # The confirmer has no write access to Payment Request, but confirming
            # the PO should logically mark the PR as done.
            if rec.payment_request_id:
                rec.payment_request_id.sudo().write({'state': 'done'})

    def action_cancel(self, cancel_reason=None):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('Cannot cancel a confirmed payment order.'))
            if rec.account_payment_id:
                if rec.account_payment_id.state not in ('draft', 'cancelled'):
                    raise UserError(_('Cannot cancel: the related Account Payment is in %s state.') % rec.account_payment_id.state)
                rec.account_payment_id.unlink()
            if rec.payment_request_id:
                rec.payment_request_id.write({
                    'state': 'canceled',
                    'payment_order_id': False,
                })
                rec.payment_request_id.sudo().message_post(
                    body=_('Payment Order %s was cancelled by %s - Reason: %s') % (
                        rec.po_number,
                        self.env.user.name,
                        cancel_reason or _('No reason provided')
                    )
                )
            rec.write({
                'state': 'canceled',
                'canceled_by': self.env.user.id,
                'canceled_date': fields.Datetime.now(),
                'cancel_reason': cancel_reason or '',
            })
            rec.message_post(body=_('Cancelled by %s - Reason: %s') % (self.env.user.name, cancel_reason or _('No reason provided')))

    def action_open_cancel_wizard(self):
        self.ensure_one()
        if self.state == 'confirmed':
            raise UserError(_('Cannot cancel a confirmed payment order.'))
        return {
            'name': _('Cancel Payment Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.order.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_order_id': self.id},
        }

    def _create_account_payment(self):
        self.ensure_one()
        payment_type = 'outbound'
        partner_type = 'customer' if self.pay_to == 'customer' else 'supplier'
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not journal:
            raise UserError(_('No bank journal found for this company.'))

        payment = self.env['account.payment'].create({
            'payment_type': payment_type,
            'partner_type': partner_type,
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'PO-{self.po_number} / PR-{self.pr_number} - {self.reason}',
            'company_id': self.env.company.id,
        })
        return payment

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('Cannot delete a confirmed payment order.'))
            if rec.account_payment_id:
                raise UserError(_('Cannot delete: unlink the related Account Payment first.'))
        return super(PaymentOrder, self).unlink()