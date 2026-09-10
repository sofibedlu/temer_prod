# -*- coding: utf-8 -*-
import logging

from markupsafe import Markup
from odoo import fields, models

from .expire_utils import compute_expire_date

_logger = logging.getLogger(__name__)

SKIP_CTX = 'skip_sunday_holiday'
SKIP_WRITE_CTX = 'skip_sunday_holiday_write'
FAST_FINAL_APPROVE_CTX = 'skip_final_approve_notify'


class SpecialApprovalWizardSkipSundayHoliday(models.Model):
    _inherit = 'special.approval.wizard'

    def _notify_users(self, users, subject, body):
        """Odoo 17: message_notify does not accept message_type."""
        if self.env.context.get(FAST_FINAL_APPROVE_CTX):
            return

        users = users.sudo().filtered(lambda u: u.active and u.partner_id)
        reservation = self.reservation_id
        if not users or not reservation:
            return

        partner_ids = users.mapped('partner_id').ids
        try:
            reservation.sudo().with_context(mail_notify_force_send=False).message_notify(
                partner_ids=partner_ids,
                subject=subject,
                body=Markup('<p>%s</p>') % body,
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:
            _logger.error('_notify_users: failed: %s', e)

    def _ensure_zero_amount_payment_config(self):
        """Zero-amount special approval must not require payment (no warning)."""
        self.ensure_one()
        reservation = self.reservation_id
        if not reservation or (self.amount or 0) > 0:
            return
        config = reservation.reservation_type_id
        if not config:
            return
        if config.amount or config.is_payment_required:
            config.sudo().write({
                'amount': 0.0,
                'is_payment_required': False,
            })

    def action_final_approve(self):
        self.ensure_one()
        reservation = self.reservation_id
        duration = self.duration or 0
        duration_in = self.duration_in or 'days'

        base_dt = fields.Datetime.now()
        if reservation:
            base_dt = fields.Datetime.to_datetime(
                reservation.expire_date or fields.Datetime.now()
            )

        ctx = {
            SKIP_WRITE_CTX: True,
            FAST_FINAL_APPROVE_CTX: True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,
        }

        _logger.info('action_final_approve: start reservation=%s', reservation.id if reservation else None)
        res = super(
            SpecialApprovalWizardSkipSundayHoliday,
            self.with_context(**ctx),
        ).action_final_approve()
        _logger.info('action_final_approve: super done reservation=%s', reservation.id if reservation else None)

        self._ensure_zero_amount_payment_config()

        if (
            reservation
            and duration > 0
            and duration_in not in ('minutes', 'hours')
            and reservation._skip_sunday_holiday_applies()
        ):
            adjusted = compute_expire_date(
                self.env, base_dt, duration, duration_in
            )
            current = fields.Datetime.to_datetime(reservation.expire_date)
            if adjusted != current:
                write_ctx = {SKIP_CTX: True, SKIP_WRITE_CTX: True}
                reservation.with_context(**write_ctx).write({
                    'expire_date': fields.Datetime.to_string(adjusted),
                })
                if reservation.property_id:
                    reservation.property_id.with_context(**write_ctx).write({
                        'reservation_end_date': adjusted,
                    })

        _logger.info('action_final_approve: done reservation=%s', reservation.id if reservation else None)

        if not res:
            return {'type': 'ir.actions.act_window_close'}
        return res
