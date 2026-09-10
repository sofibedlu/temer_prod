# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, models


class PropertyReservationEndDateBuffer(models.Model):
    _inherit = 'property.reservation'

    special_duration = fields.Integer(tracking=True)

    def _get_approval_end_date_buffer(self, minutes=5):
        """Return expire_date extended by the approval grace period."""
        self.ensure_one()
        if not self.expire_date:
            return False
        new_expire_date = fields.Datetime.to_datetime(self.expire_date) + timedelta(
            minutes=minutes,
        )
        return fields.Datetime.to_string(new_expire_date)

    def _add_approval_end_date_buffer(self, minutes=5):
        """Extend expire_date to give approvers time before the reservation expires."""
        for reservation in self:
            new_expire_date = reservation._get_approval_end_date_buffer(minutes=minutes)
            if new_expire_date:
                reservation.sudo().write({'expire_date': new_expire_date})
