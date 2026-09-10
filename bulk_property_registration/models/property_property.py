# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    bulk_registration_id = fields.Many2one(
        'property.bulk.registration',
        string='Bulk Registration',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    @api.depends('site.name', 'block.name', 'floor_id.name', 'property_type_id.code', 'unit_number')
    def _compute_property_name(self):
        """When unit_number is set, include it in name so multiple units per floor have unique names."""
        for rec in self:
            if rec.site and rec.block and rec.floor_id and rec.property_type_id:
                if getattr(rec, 'unit_number', None) and rec.unit_number.strip():
                    rec.name = '%s-%s-F%s-%s' % (
                        rec.site.name or '',
                        rec.block.name or '',
                        rec.floor_id.name,
                        rec.unit_number.strip(),
                    )
                else:
                    rec.name = '%s-%s-F%s-%s' % (
                        rec.site.name or '',
                        rec.block.name or '',
                        rec.floor_id.name,
                        rec.property_type_id.code or '',
                    )
            else:
                rec.name = _('New')
