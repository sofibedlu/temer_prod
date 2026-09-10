# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommercialRateRange(models.Model):
    _name = 'commercial.rate.range'
    _description = 'Commercial Rate Range'
    _rec_name = 'display_name'

    rate_min = fields.Float(string='Min', required=True)
    rate_max = fields.Float(string='Max', required=True)
    display_name = fields.Char(
        string='Rate Range',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('rate_min', 'rate_max')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.rate_min} - {rec.rate_max}"

    @api.constrains('rate_min', 'rate_max')
    def _check_rate_range(self):
        for rec in self:
            if rec.rate_max <= rec.rate_min:
                raise ValidationError("Max must be greater than Min.")
