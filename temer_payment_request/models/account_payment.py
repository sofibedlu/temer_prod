# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_order_id = fields.Many2one(
        'payment.order',
        string='Payment Order',
        compute='_compute_payment_order',
    )

    payment_request_id = fields.Many2one(
        'payment.request',
        string='Payment Request',
        compute='_compute_payment_request',
    )

    payment_request_reason = fields.Text(
        string='Payment Request Reason',
        related='payment_request_id.reason',
        readonly=True,
    )

    is_editable_by_user = fields.Boolean(
        string='Editable by Current User',
        compute='_compute_is_editable_by_user',
    )

    @api.depends('ref')
    def _compute_payment_order(self):
        for rec in self:
            po = self.env['payment.order'].search([
                ('account_payment_id', '=', rec.id),
            ], limit=1)
            rec.payment_order_id = po.id if po else False

    @api.depends('payment_order_id')
    def _compute_payment_request(self):
        for rec in self:
            rec.payment_request_id = rec.payment_order_id.payment_request_id.id if rec.payment_order_id else False

    @api.depends('payment_order_id')
    def _compute_is_editable_by_user(self):
        is_handler = self.env.user.has_group('temer_payment_request.group_account_payment_handler')
        for rec in self:
            if rec.payment_order_id:
                rec.is_editable_by_user = is_handler
            else:
                rec.is_editable_by_user = True

    def write(self, vals):
        # Track old values before write for connected PO/PR logging
        old_values = {}
        for rec in self:
            if rec.payment_order_id:
                is_handler = self.env.user.has_group('temer_payment_request.group_account_payment_handler')
                if not is_handler:
                    raise UserError(_(
                        "You do not have permission to edit this payment. "
                        "It was automatically generated from Payment Order %(po)s. "
                        "Please contact an Account Payment Handler to make changes.",
                        po=rec.payment_order_id.po_number,
                    ))
                old_values[rec.id] = {
                    'partner_id': rec.partner_id.id,
                    'partner_name': rec.partner_id.name if rec.partner_id else _('None'),
                    'amount': rec.amount,
                    'currency_id': rec.currency_id.id,
                    'currency_name': rec.currency_id.name if rec.currency_id else _('None'),
                    'date': rec.date,
                    'journal_id': rec.journal_id.id,
                    'journal_name': rec.journal_id.name if rec.journal_id else _('None'),
                    'payment_type': rec.payment_type,
                    'partner_type': rec.partner_type,
                    'ref': rec.ref or '',
                }

        result = super(AccountPayment, self).write(vals)

        # Post changes on connected PO and PR chatter (using sudo to avoid access issues)
        for rec in self:
            if rec.payment_order_id and rec.id in old_values:
                old = old_values[rec.id]
                changes = []

                if 'partner_id' in vals:
                    new_partner = self.env['res.partner'].browse(vals['partner_id']) if vals['partner_id'] else False
                    new_name = new_partner.name if new_partner else _('None')
                    if old['partner_name'] != new_name:
                        changes.append(_('Partner changed from "%s" to "%s"') % (old['partner_name'], new_name))

                if 'amount' in vals:
                    if float_compare(old['amount'], vals['amount'], precision_rounding=rec.currency_id.rounding) != 0:
                        changes.append(_('Amount changed from %s %s to %s %s') % (
                            old['amount'], old['currency_name'],
                            vals['amount'], rec.currency_id.name
                        ))

                if 'date' in vals:
                    if old['date'] != vals['date']:
                        changes.append(_('Date changed from %s to %s') % (old['date'], vals['date']))

                if 'journal_id' in vals:
                    new_journal = self.env['account.journal'].browse(vals['journal_id']) if vals['journal_id'] else False
                    new_name = new_journal.name if new_journal else _('None')
                    if old['journal_name'] != new_name:
                        changes.append(_('Journal changed from "%s" to "%s"') % (old['journal_name'], new_name))

                if 'payment_type' in vals:
                    old_label = dict(self._fields['payment_type'].selection).get(old['payment_type'], old['payment_type'])
                    new_label = dict(self._fields['payment_type'].selection).get(vals['payment_type'], vals['payment_type'])
                    if old['payment_type'] != vals['payment_type']:
                        changes.append(_('Payment Type changed from "%s" to "%s"') % (old_label, new_label))

                if 'partner_type' in vals:
                    old_label = dict(self._fields['partner_type'].selection).get(old['partner_type'], old['partner_type'])
                    new_label = dict(self._fields['partner_type'].selection).get(vals['partner_type'], vals['partner_type'])
                    if old['partner_type'] != vals['partner_type']:
                        changes.append(_('Partner Type changed from "%s" to "%s"') % (old_label, new_label))

                if 'ref' in vals:
                    new_ref = vals['ref'] or ''
                    if old['ref'] != new_ref:
                        changes.append(_('Reference changed from "%s" to "%s"') % (old['ref'], new_ref))

                if changes:
                    nl = chr(10)
                    bullet = chr(8226) + ' '
                    bullet_changes = (nl + bullet).join(changes)
                    message_body = _('Account Payment edited by %s:') % self.env.user.name + nl + bullet + bullet_changes

                    # Post on connected Payment Order (sudo to ensure it works)
                    rec.payment_order_id.sudo().message_post(body=message_body)

                    # Post on connected Payment Request (sudo to ensure it works)
                    if rec.payment_request_id:
                        rec.payment_request_id.sudo().message_post(
                            body=_('Linked Account Payment was edited by %s:') % self.env.user.name + nl + bullet + bullet_changes
                        )

        return result

    def action_post(self):
        """Override to notify linked PO and PR when payment is posted."""
        # Store linked records before posting (state changes after super)
        linked_records = []
        for rec in self:
            if rec.payment_order_id:
                linked_records.append({
                    'record': rec,
                    'po': rec.payment_order_id,
                    'pr': rec.payment_request_id,
                })

        result = super(AccountPayment, self).action_post()

        # Post notifications after successful posting
        for item in linked_records:
            rec = item['record']
            po = item['po']
            pr = item['pr']
            user_name = self.env.user.name

            # Post on Account Payment's own chatter
            rec.sudo().message_post(
                body=_('Account Payment posted by %s') % user_name
            )

            # Post on linked Payment Order chatter
            po.sudo().message_post(
                body=_('Linked Account Payment was posted by %s') % user_name
            )

            # Post on linked Payment Request chatter
            if pr:
                pr.sudo().message_post(
                    body=_('Linked Account Payment was posted by %s') % user_name
                )

        return result

    def action_cancel(self):
        """Override to notify linked PO and PR when payment is cancelled."""
        # Store linked records before cancelling (state changes after super)
        linked_records = []
        for rec in self:
            if rec.payment_order_id:
                linked_records.append({
                    'record': rec,
                    'po': rec.payment_order_id,
                    'pr': rec.payment_request_id,
                })

        result = super(AccountPayment, self).action_cancel()

        # Post notifications after successful cancellation
        for item in linked_records:
            rec = item['record']
            po = item['po']
            pr = item['pr']
            user_name = self.env.user.name

            # Post on Account Payment's own chatter
            rec.sudo().message_post(
                body=_('Account Payment cancelled by %s') % user_name
            )

            # Post on linked Payment Order chatter
            po.sudo().message_post(
                body=_('Linked Account Payment was cancelled by %s') % user_name
            )

            # Post on linked Payment Request chatter
            if pr:
                pr.sudo().message_post(
                    body=_('Linked Account Payment was cancelled by %s') % user_name
                )

        return result

    def action_open_cancel_wizard(self):
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('This payment is already cancelled.'))
        return {
            'name': _('Cancel Account Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_account_payment_id': self.id},
        }

    def unlink(self):
        for rec in self:
            po = self.env['payment.order'].search([
                ('account_payment_id', '=', rec.id),
            ], limit=1)
            if po:
                raise UserError(_(
                    "You cannot delete this payment because it was automatically generated "
                    "from Payment Order %(po)s.",
                    po=po.po_number,
                ))
        return super(AccountPayment, self).unlink()