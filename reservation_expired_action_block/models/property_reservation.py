# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError

BLOCKED_RESERVATION_STATUSES = ('expired', 'canceled')
EXPIRY_EXEMPT_STATUSES = ('sold',)


class PropertyReservationExpiredBlock(models.Model):
    _inherit = 'property.reservation'

    def _is_expired_or_canceled(self):
        """Return True when the reservation must not be converted or approved."""
        self.ensure_one()
        if self.status in BLOCKED_RESERVATION_STATUSES:
            return True
        if (
            self.expire_date
            and self.status not in EXPIRY_EXEMPT_STATUSES
            and fields.Datetime.now() > self.expire_date
        ):
            return True
        return False

    def _raise_if_expired_or_canceled(self, message):
        for rec in self:
            if rec._is_expired_or_canceled():
                raise ValidationError(message)

    def _check_reservation_active_for_convert(self):
        self._raise_if_expired_or_canceled(_(
            "This reservation is expired or canceled. It cannot be converted."
        ))

    def _check_reservation_active_for_approve(self):
        self._raise_if_expired_or_canceled(_(
            "This reservation is expired or canceled. Approval actions are not allowed."
        ))

    def _check_reservation_active_for_extend(self):
        self._raise_if_expired_or_canceled(_(
            "This reservation is expired or canceled. Extension actions are not allowed."
        ))

    def _check_reservation_active_for_confirm_sales(self):
        self._raise_if_expired_or_canceled(_(
            "This reservation is expired or canceled. Confirm Sales is not allowed."
        ))

    def action_convert_to_special(self):
        self._check_reservation_active_for_convert()
        return super().action_convert_to_special()

    def action_convert_to_regular(self):
        self._check_reservation_active_for_convert()
        return super().action_convert_to_regular()

    def action_request_special_approval(self):
        self._check_reservation_active_for_approve()
        return super().action_request_special_approval()

    def action_view_special_approval(self):
        self._check_reservation_active_for_approve()
        return super().action_view_special_approval()

    def action_confirm_sales(self):
        self._check_reservation_active_for_confirm_sales()
        return super().action_confirm_sales()

    def reservation_extend(self):
        self._check_reservation_active_for_extend()
        return super().reservation_extend()
