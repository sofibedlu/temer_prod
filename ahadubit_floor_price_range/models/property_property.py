# -*- coding: utf-8 -*-
from odoo import models, api

from .floor_price_range import _floor_name_to_number


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    def _get_effective_floor_number(self, rec):
        """Floor number from floor_id or single floor_ids (for draft form)."""
        if rec.floor_id:
            return rec.floor_id.name
        if rec.floor_ids and len(rec.floor_ids) == 1:
            return rec.floor_ids[0].name
        return None

    def _get_price_from_floor_range(self, site, floor_number):
        """Price from floor price range for this site and floor, or None."""
        if not site or floor_number is None or not site.floor_price_range_ids:
            return None
        n_floor = _floor_name_to_number(floor_number)
        if n_floor is None:
            return None
        for r in site.floor_price_range_ids:
            if not r.floor_from_id or not r.floor_to_id:
                continue
            n_from = _floor_name_to_number(r.floor_from_id.name)
            n_to = _floor_name_to_number(r.floor_to_id.name)
            if n_from is not None and n_to is not None and n_from <= n_floor <= n_to:
                return r.price
        return None

    @api.depends('site', 'floor_id', 'floor_ids')
    def compute_unit_price(self):
        """Price(m2) from floor price range for this site and floor.

        If another module (e.g. Price(m2) Edit) has set an override_price_m2,
        we do not touch price here; that module will handle it.
        """
        for rec in self:
            if getattr(rec, 'override_price_m2', None):
                continue
            if not rec.site:
                rec.price = 0
                continue
            floor_number = self._get_effective_floor_number(rec)
            price_from_range = self._get_price_from_floor_range(rec.site, floor_number)
            rec.price = price_from_range if price_from_range is not None else 0

    @api.onchange('site', 'floor_id', 'floor_ids')
    def _onchange_floor_price_from_range(self):
        """Update Price(m2) in the form when site or floor changes (before save).

        If override_price_m2 is set, keep the manual value.
        """
        if not self.site or getattr(self, 'override_price_m2', None):
            return
        floor_number = self._get_effective_floor_number(self)
        price_from_range = self._get_price_from_floor_range(self.site, floor_number)
        self.price = price_from_range if price_from_range is not None else 0

    def write(self, vals):
        # When user selects a single floor via floor_ids (draft), persist it to floor_id
        # so the stored computed price runs and floor price range is applied
        if 'floor_ids' in vals and not vals.get('floor_id'):
            floor_ids = []
            for command in vals.get('floor_ids') or []:
                if command[0] == 6:
                    floor_ids = list(command[2]) if len(command) > 2 else []
                    break
                if command[0] == 4:
                    floor_ids.append(command[1])
            if len(floor_ids) == 1:
                vals['floor_id'] = floor_ids[0]
        return super().write(vals)
