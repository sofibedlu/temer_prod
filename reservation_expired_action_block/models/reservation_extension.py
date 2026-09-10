# -*- coding: utf-8 -*-
from odoo import api, models, _


class PropertyReservationExtendExpiredBlock(models.Model):
    _inherit = 'property.reservation.extend.history'

    def _check_linked_reservation_active_for_extension(self):
        for rec in self:
            if rec.reservation_id:
                rec.reservation_id._check_reservation_active_for_extend()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reservation_id'):
                reservation = self.env['property.reservation'].browse(vals['reservation_id'])
                reservation._check_reservation_active_for_extend()
        return super().create(vals_list)

    def approve_extension(self):
        self._check_linked_reservation_active_for_extension()
        return super().approve_extension()

    def action_final_approve_extension(self):
        self._check_linked_reservation_active_for_extension()
        return super().action_final_approve_extension()
