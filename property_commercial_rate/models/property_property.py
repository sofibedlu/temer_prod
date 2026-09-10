# -*- coding: utf-8 -*-
from odoo import models, fields


class PropertyPropertyCommercialRate(models.Model):
    _inherit = 'property.property'

    commercial_rate_range_id = fields.Many2one(
        'commercial.rate.range',
        string='Commercial Rate Range',
    )
