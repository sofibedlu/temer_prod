# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentCancelWizard(models.TransientModel):
    _name = 'account.payment.cancel.wizard'
    _description = 'Account Payment Cancel Wizard'

    account_payment_id = fields.Many2one(
        'account.payment',
        string='Account Payment',
        required=True,
        readonly=True,
    )
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        required=True,
    )

    def action_confirm_cancel(self):
        self.ensure_one()
        is_handler = self.env.user.has_group('temer_payment_request.group_account_payment_handler')
        is_manager = self.env.user.has_group('temer_payment_request.group_payment_request_manager')
        if not is_handler and not is_manager:
            raise UserError(_("You don't have permission to cancel account payments."))
        if not self.cancel_reason or not self.cancel_reason.strip():
            raise UserError(_('Please provide a cancellation reason.'))

        payment = self.account_payment_id
        po = payment.payment_order_id
        pr = payment.payment_request_id
        user_name = self.env.user.name
        reason = self.cancel_reason

        # Cancel the Account Payment first
        payment.action_cancel()
        payment.sudo().message_post(
            body=_('Cancelled by %s - Reason: %s') % (user_name, reason)
        )

        # Cancel the linked Payment Order
        if po:
            po.sudo().write({
                'state': 'canceled',
                'canceled_by': self.env.user.id,
                'canceled_date': fields.Datetime.now(),
                'cancel_reason': reason,
            })
            po.sudo().message_post(
                body=_('Cancelled by %s - Reason: %s') % (user_name, reason)
            )

        # Cancel the linked Payment Request
        if pr:
            pr.sudo().write({
                'state': 'canceled',
                'payment_order_id': False,
            })
            pr.sudo().message_post(
                body=_('Account Payment was cancelled by %s - Reason: %s') % (user_name, reason)
            )

        return {'type': 'ir.actions.act_window_close'}