# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommercialGrossRange(models.Model):
    _name = 'commercial.gross.range'
    _description = 'Commercial Gross Range'
    _rec_name = 'display_name'
    _order = 'gross_min'

    gross_min = fields.Float(string='Min (m²)', required=True, digits=(16, 2))
    gross_max = fields.Float(string='Max (m²)', required=True, digits=(16, 2))
    display_name = fields.Char(
        string='Gross Range',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('gross_min', 'gross_max')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.gross_min} - {rec.gross_max} m²"

    @api.constrains('gross_min', 'gross_max')
    def _check_gross_range(self):
        for rec in self:
            if rec.gross_max <= rec.gross_min:
                raise ValidationError("Max must be greater than Min.")
