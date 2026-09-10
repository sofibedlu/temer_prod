# -*- coding: utf-8 -*-
from odoo import models, fields


class PropertyReservationDurationFix(models.Model):
    _inherit = 'property.reservation'

    special_duration_in = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Special Duration Unit', default='days')
