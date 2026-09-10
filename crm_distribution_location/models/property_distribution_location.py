# -*- coding: utf-8 -*-
from odoo import fields, models


class PropertyDistributionLocation(models.Model):
    _name = "property.distribution.location"
    _description = "Lead Distribution Location"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Location name must be unique."),
    ]
