# -*- coding: utf-8 -*-
from odoo import models


class PropertyFloor(models.Model):
    """Order floors by number so Floor From/To dropdowns show 1, 2, 3, ... (not 1, 10, 11, 2, ...)."""
    _inherit = 'property.floor'
    _order = 'name'
