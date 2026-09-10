# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentOrderCancelWizard(models.TransientModel):
    _name = 'payment.order.cancel.wizard'
    _description = 'Payment Order Cancel Wizard'

    payment_order_id = fields.Many2one(
        'payment.order',
        string='Payment Order',
        required=True,
        readonly=True,
    )
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        required=True,
    )

    def action_confirm_cancel(self):
        self.ensure_one()
        if not self.cancel_reason or not self.cancel_reason.strip():
            raise UserError(_('Please provide a cancellation reason.'))

        po = self.payment_order_id
        pr = po.payment_request_id
        user_name = self.env.user.name
        reason = self.cancel_reason

        # Unlink the linked Account Payment if it's still draft
        if po.account_payment_id:
            if po.account_payment_id.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    'Cannot cancel: the related Account Payment is in %s state.'
                ) % po.account_payment_id.state)
            po.account_payment_id.unlink()

        # Cancel the Payment Order
        po.write({
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
            pr.write({
                'state': 'canceled',
                'payment_order_id': False,
            })
            pr.sudo().message_post(
                body=_('Payment Order %s was cancelled by %s - Reason: %s') % (
                    po.po_number, user_name, reason
                )
            )

        return {'type': 'ir.actions.act_window_close'}