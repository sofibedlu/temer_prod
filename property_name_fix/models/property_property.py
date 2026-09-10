# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PropertyProperty(models.Model):
    """Fix property name generation: use house number (unit_number) instead of type code.

    Format: {Site}-{Block}-F{Floor}-{HouseNumber}
    Example: PAN-AJWA1 SHOP-01-F4-003
    """

    _inherit = 'property.property'

    @api.depends('site.name', 'block.name', 'floor_id.name', 'unit_number')
    def _compute_property_name(self):
        for rec in self:
            if rec.site and rec.block and rec.floor_id:
                site = rec.site.name or ''
                block = rec.block.name or ''
                floor = rec.floor_id.name or ''
                unit = getattr(rec, 'unit_number', None)
                unit = str(unit).strip() if unit and str(unit).strip() else ''

                if unit:
                    rec.name = f"{site}-{block}-F{floor}-{unit}"
                else:
                    rec.name = f"{site}-{block}-F{floor}"
            else:
                rec.name = _('New')
