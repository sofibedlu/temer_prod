# -*- coding: utf-8 -*-

from odoo import fields, models


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    property_type = fields.Selection(
        selection_add=[('office', 'Office')],
        ondelete={'office': 'set default'},
    )
