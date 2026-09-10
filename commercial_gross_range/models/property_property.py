# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PropertyPropertyCommercialGrossRange(models.Model):
    _inherit = 'property.property'

    commercial_gross_range_id = fields.Many2one(
        'commercial.gross.range',
        string='Gross Area',
        help='Commercial gross range; sales price uses the maximum m2 of the range.',
    )
    commercial_gross_area_mode = fields.Selection(
        [
            ('range', 'Range'),
            ('normal', 'Normal'),
        ],
        string='Commercial Gross Area',
        default='range',
        help='Use a configured range or enter the commercial gross area manually.',
    )

    def _commercial_gross_range_max_area(self):
        """Max m2 from the selected gross range (used for sales price)."""
        self.ensure_one()
        if self.commercial_gross_range_id:
            return self.commercial_gross_range_id.gross_max or 0.0
        return 0.0

    def _commercial_gross_uses_range(self, vals=None):
        self.ensure_one()
        vals = vals or {}
        mode = vals.get('commercial_gross_area_mode', self.commercial_gross_area_mode)
        return mode != 'normal'

    def _apply_commercial_gross_range_max(self):
        """Store range on commercial_gross_range_id; set gross fields to range max."""
        for rec in self:
            if rec.property_type != 'commercial' or not rec._commercial_gross_uses_range():
                continue
            gross_max = rec._commercial_gross_range_max_area()
            if gross_max > 0:
                rec.property_type_gross_area = gross_max
                rec.gross_area = gross_max
            elif not rec.commercial_gross_range_id:
                rec.property_type_gross_area = 0.0

    def _vals_from_commercial_gross_range(self, vals):
        range_id = vals.get('commercial_gross_range_id')
        if not range_id:
            vals['property_type_gross_area'] = 0.0
            return
        gross_range = self.env['commercial.gross.range'].browse(range_id)
        gross_max = gross_range.gross_max or 0.0
        if gross_max > 0:
            vals['property_type_gross_area'] = gross_max
            vals['gross_area'] = gross_max

    def _sync_commercial_gross_vals(self, vals):
        """When commercial gross range changes, push max into gross fields for pricing."""
        if 'commercial_gross_range_id' not in vals:
            return
        if self:
            commercial = self.filtered(
                lambda r: r.property_type == 'commercial' and r._commercial_gross_uses_range(vals)
            )
            if commercial and len(commercial) == len(self):
                self._vals_from_commercial_gross_range(vals)
        elif vals.get('commercial_gross_range_id') and vals.get('commercial_gross_area_mode') != 'normal':
            self._vals_from_commercial_gross_range(vals)

    @api.onchange('commercial_gross_range_id', 'property_type', 'commercial_gross_area_mode')
    def _onchange_commercial_gross_range_id(self):
        if self.property_type != 'commercial':
            self.commercial_gross_range_id = False
            self.commercial_gross_area_mode = False
            return
        if not self.commercial_gross_area_mode:
            self.commercial_gross_area_mode = 'range'
        if self.commercial_gross_area_mode == 'normal':
            self.commercial_gross_range_id = False
            return
        gross_max = self._commercial_gross_range_max_area()
        if gross_max > 0:
            self.property_type_gross_area = gross_max
            self.gross_area = gross_max
        else:
            self.property_type_gross_area = 0.0
        if hasattr(self, '_onchange_property_type_details'):
            self._onchange_property_type_details()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('property_type') not in (None, False, 'commercial'):
                vals.pop('commercial_gross_range_id', None)
                vals['commercial_gross_area_mode'] = False
                continue
            if vals.get('property_type') == 'commercial' and not vals.get('commercial_gross_area_mode'):
                vals['commercial_gross_area_mode'] = 'range'
            if vals.get('commercial_gross_area_mode') == 'normal':
                vals['commercial_gross_range_id'] = False
                continue
            if vals.get('commercial_gross_range_id'):
                self._vals_from_commercial_gross_range(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('property_type') and vals['property_type'] != 'commercial':
            vals['commercial_gross_range_id'] = False
            vals['commercial_gross_area_mode'] = False
        elif (
            vals.get('property_type') == 'commercial'
            and 'commercial_gross_area_mode' not in vals
            and all(rec.property_type != 'commercial' for rec in self)
        ):
            vals['commercial_gross_area_mode'] = 'range'
        elif vals.get('commercial_gross_area_mode') == 'normal':
            vals['commercial_gross_range_id'] = False
        if 'commercial_gross_range_id' in vals:
            self._sync_commercial_gross_vals(vals)
        elif (
            'property_type_gross_area' in vals
            and 'commercial_gross_range_id' not in vals
            and len(self) == 1
            and self.property_type == 'commercial'
            and self.commercial_gross_range_id
            and self._commercial_gross_uses_range(vals)
        ):
            # Commercial gross is chosen by range; numeric gross stays at range max
            gross_max = self._commercial_gross_range_max_area()
            vals['property_type_gross_area'] = gross_max
            vals['gross_area'] = gross_max
        return super().write(vals)
