# -*- coding: utf-8 -*-
from odoo import models


class PropertyReservationExtendEndDateBuffer(models.Model):
    _inherit = 'property.reservation.extend.history'

    def approve_extension(self):
        super().approve_extension()
        for rec in self:
            if rec.reservation_id:
                rec.reservation_id._add_approval_end_date_buffer()
