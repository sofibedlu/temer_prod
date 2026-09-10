# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PropertyReservationPaymentTab(models.Model):
    _inherit = 'property.reservation'

    show_payment_tab = fields.Boolean(
        compute='_compute_show_payment_tab',
        string='Show Payment Tab',
    )

    @api.depends(
        'is_payment_required',
        'state',
        'is_special_reservation',
        'make_special_reservation',
        'reservation_type_id.reservation_type',
    )
    def _compute_show_payment_tab(self):
        for rec in self:
            rec.show_payment_tab = (
                rec.is_payment_required
                or rec.state == 'approved'
                or rec.is_special_reservation
                or rec.make_special_reservation
                or (
                    rec.reservation_type_id
                    and rec.reservation_type_id.reservation_type == 'special'
                )
            )
