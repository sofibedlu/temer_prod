# -*- coding: utf-8 -*-
from odoo import fields, models


class PropertySite(models.Model):
    _inherit = 'property.site'

    number_of_floors = fields.Integer(
        string='Number of Floors',
        help='Total floors in this site (e.g. 4 means floors 1 to 4). Used for bulk property registration.',
    )
