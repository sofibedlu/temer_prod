# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


def _floor_name_to_number(name):
    """Convert floor name (int or str like '1','10') to numeric for comparison."""
    if name is None:
        return None
    try:
        return int(name) if isinstance(name, (int, float)) else int(str(name).strip())
    except (ValueError, TypeError):
        return None


class FloorPriceRange(models.Model):
    _name = 'floor.price.range'
    _description = 'Floor Price Range'
    _order = 'site_id, floor_from_id'

    site_id = fields.Many2one(
        'property.site',
        string='Site',
        required=True,
        ondelete='cascade',
    )
    floor_from_id = fields.Many2one(
        'property.floor',
        string='Floor From',
        required=True,
        ondelete='restrict',
    )
    floor_to_id = fields.Many2one(
        'property.floor',
        string='Floor To',
        required=True,
        ondelete='restrict',
    )
    price = fields.Monetary(
        string='Price per m2',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='site_id.currency_id',
        store=True,
        readonly=True,
    )

    def _get_site_floor_count(self, site):
        """Get floor count from site: number_of_floors, floor_id (temer), or from properties."""
        if not site:
            return None
        if site.number_of_floors and site.number_of_floors >= 1:
            return site.number_of_floors
        if hasattr(site, 'floor_id') and site.floor_id and site.floor_id.id:
            try:
                n = site.floor_id.name
                return int(n) if isinstance(n, (int, float)) else int(str(n).strip())
            except (ValueError, TypeError):
                pass
        props = self.env['property.property'].search([('site', '=', site.id)])
        floors = props.mapped('floor_id')
        if not floors:
            return None
        nums = [_floor_name_to_number(f.name) for f in floors if _floor_name_to_number(f.name) is not None]
        return max(nums) if nums else None

    @api.depends(
        'site_id', 'site_id.number_of_floors',
        'site_id.floor_price_range_ids.floor_from_id',
        'site_id.floor_price_range_ids.floor_to_id',
    )
    def _compute_floor_ids_available(self):
        """Floors 1 to N from the selected site (N = site floor count).
        Excludes floors used as boundaries in OTHER ranges of the same site,
        so when editing a range you can change it without overlap; when creating
        you pick from floors not yet used.
        """
        Floor = self.env['property.floor']
        Range = self.env['floor.price.range']
        Property = self.env['property.property']
        for rec in self:
            if not rec.site_id:
                rec.floor_ids_available = Floor.search([])
                continue

            site_floor_count = rec._get_site_floor_count(rec.site_id)
            if site_floor_count and site_floor_count >= 1:
                names = list(range(1, site_floor_count + 1)) + [str(x) for x in range(1, site_floor_count + 1)]
                site_floors = Floor.search([('name', 'in', names)]).sorted(
                    key=lambda f: (_floor_name_to_number(f.name) or 0, str(f.name))
                )
            else:
                used_floors = Property.search([('site', '=', rec.site_id.id)]).mapped('floor_id')
                site_floors = used_floors.sorted(
                    key=lambda f: (_floor_name_to_number(f.name) or 0, str(f.name))
                ) if used_floors else Floor.search([]).sorted(
                    key=lambda f: (_floor_name_to_number(f.name) or 0, str(f.name))
                )

            # Include both DB records and other rows in same recordset (editable tree)
            if rec.id:
                other_ranges = Range.search([
                    ('site_id', '=', rec.site_id.id),
                    ('id', '!=', rec.id),
                ])
            else:
                other_ranges = Range.search([
                    ('site_id', '=', rec.site_id.id),
                ])
            others_in_self = self.filtered(
                lambda r: r.site_id == rec.site_id and r != rec
                and r.floor_from_id and r.floor_to_id
            )
            other_ranges = other_ranges | others_in_self
            # Exclude ALL floors covered by other ranges (1-4 means 1,2,3,4 all excluded)
            excluded_floors = Floor.browse([])
            for other in other_ranges:
                o_from = _floor_name_to_number(other.floor_from_id.name) if other.floor_from_id else None
                o_to = _floor_name_to_number(other.floor_to_id.name) if other.floor_to_id else None
                if o_from is None or o_to is None:
                    continue
                for f in site_floors:
                    n = _floor_name_to_number(f.name)
                    if n is not None and o_from <= n <= o_to:
                        excluded_floors |= f
            rec.floor_ids_available = site_floors - excluded_floors

    floor_ids_available = fields.Many2many(
        'property.floor',
        compute='_compute_floor_ids_available',
        string='Floors of site',
        store=False,
    )

    @api.constrains('site_id', 'floor_from_id', 'floor_to_id')
    def _check_floor_range_and_overlap(self):
        """Ensure From <= To (numeric) and no overlap with other ranges for same site."""
        for rec in self:
            if not rec.floor_from_id or not rec.floor_to_id:
                continue
            n_from = _floor_name_to_number(rec.floor_from_id.name)
            n_to = _floor_name_to_number(rec.floor_to_id.name)
            if n_from is not None and n_to is not None and n_from > n_to:
                raise ValidationError(
                    _('Floor From must be smaller than or equal to Floor To.')
                )
            if not rec.site_id:
                continue
            other_ranges = self.search([
                ('site_id', '=', rec.site_id.id),
                ('id', '!=', rec.id),
                ('floor_from_id', '!=', False),
                ('floor_to_id', '!=', False),
            ])
            for other in other_ranges:
                o_from = _floor_name_to_number(other.floor_from_id.name)
                o_to = _floor_name_to_number(other.floor_to_id.name)
                if o_from is None or o_to is None or n_from is None or n_to is None:
                    continue
                if n_from <= o_to and o_from <= n_to:
                    raise ValidationError(
                        _('This range (%s–%s) overlaps with existing range %s–%s for site %s. '
                          'Ranges must not overlap.')
                        % (rec.floor_from_id.name, rec.floor_to_id.name,
                           other.floor_from_id.name, other.floor_to_id.name, rec.site_id.name)
                    )

    def _recompute_property_prices(self):
        """Recompute Price(m2) for properties using this site."""
        if not self:
            return
        sites = self.mapped('site_id')
        if not sites:
            return
        props = self.env['property.property'].search([('site', 'in', sites.ids)])
        if props:
            props.compute_unit_price()
            props.compute_total_price()

    def create(self, vals_list):
        res = super().create(vals_list)
        res._recompute_property_prices()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._recompute_property_prices()
        return res

    def unlink(self):
        sites = self.mapped('site_id')
        res = super().unlink()
        if sites:
            props = self.env['property.property'].search([('site', 'in', sites.ids)])
            if props:
                props.compute_unit_price()
                props.compute_total_price()
        return res
