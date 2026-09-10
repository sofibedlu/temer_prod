# -*- coding: utf-8 -*-
from odoo import models, api

_APPROVAL_STATES = ('submitted', 'supervisor', 'manager', 'ceo', 'approved')


class PropertyReservationPaymentCommit(models.Model):
    _inherit = 'property.reservation.payment'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        to_commit = records.filtered(
            lambda r: r.is_wizard_temp
            and r.reservation_id
            and r.reservation_id.state in _APPROVAL_STATES
        )
        if to_commit:
            to_commit.sudo().write({
                'is_wizard_temp': False,
                'is_new_line': False,
            })
        return records
