# -*- coding: utf-8 -*-
##############################################################################
#    Property Lock / Unlock
#    Copyright (C) 2024-TODAY Ahadubit Technologies
##############################################################################

from odoo import models, fields


class PropertySpecialDiscount(models.Model):
    _inherit = 'property.special.discount'

    # Exclude locked properties from special discount
    property_id = fields.Many2one(
        'property.property',
        domain=[('state', 'in', ['available']), ('is_locked', '=', False)],
        string="Property",
        required=True
    )
