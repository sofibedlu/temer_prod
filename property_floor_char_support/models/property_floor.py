# -*- coding: utf-8 -*-
##############################################################################
#
#    Property Floor Character Support
#    Copyright (C) 2024-TODAY Ahadubit Technologies
#
#    This program is distributed under the terms of the GNU Lesser
#    General Public License (LGPL v3).
#
##############################################################################

from odoo import models, fields


class PropertyFloor(models.Model):
    _inherit = 'property.floor'

    # Override: change name from Integer to Char so it accepts letters and special characters
    name = fields.Char(string="name", required=True)
