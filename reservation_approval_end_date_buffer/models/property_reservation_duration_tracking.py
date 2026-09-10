# -*- coding: utf-8 -*-
from odoo import fields, models


class PropertyReservationDurationTracking(models.Model):
    _inherit = 'property.reservation'

    special_duration_in = fields.Selection(
        selection=[
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
        ],
        tracking=True,
    )
