# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .temer_report_export import temer_export_act_url


class PropertyReservationReport(models.Model):
    _inherit = 'property.reservation'

    report_property_type_stored = fields.Selection(
        related='property_id.property_type',
        string='Property Type',
        store=True,
    )
    report_bedroom_stored = fields.Integer(
        related='property_id.bedroom',
        string='Bedrooms',
        store=True,
    )
    report_property_type = fields.Char(
        string='Property Type',
        compute='_compute_report_unit_type',
    )
    report_unit_type = fields.Char(
        string='Unit Type',
        compute='_compute_report_unit_type',
    )
    report_total_payment = fields.Float(
        string='Reservation Payment',
        compute='_compute_report_payment_fields',
    )

    def action_temer_export_reservation_history(self):
        return temer_export_act_url(
            self,
            'reservation_history',
            [],
        )

    @api.depends('property_id', 'property_id.property_type', 'property_id.bedroom')
    def _compute_report_unit_type(self):
        for reservation in self:
            prop = reservation.property_id
            if not prop:
                reservation.report_property_type = '-'
                reservation.report_unit_type = '-'
                continue

            ptype = prop.property_type or ''
            reservation.report_property_type = ptype.capitalize() if ptype else '-'
            if ptype == 'commercial':
                reservation.report_unit_type = '0'
            else:
                bedrooms = prop.bedroom or 0
                reservation.report_unit_type = '{}BR'.format(bedrooms) if bedrooms else '-'

    @api.depends(
        'payment_line_ids.amount',
        'payment_line_ids.payment_status',
    )
    def _compute_report_payment_fields(self):
        for reservation in self:
            payments = reservation.payment_line_ids
            reservation.report_total_payment = sum(payments.mapped('amount'))
