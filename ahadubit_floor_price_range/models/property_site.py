# -*- coding: utf-8 -*-
from odoo import models, fields, api

from .floor_price_range import _floor_name_to_number


class PropertySite(models.Model):
    _inherit = 'property.site'

    number_of_floors = fields.Integer(
        string='Number of Floors',
        help='Total floors in this site (e.g. 10 = floors 1 to 10). Used for floor price range from/to options.',
    )
    # Allow saving 0 for Price per m2 on registration site
    price_per_m2 = fields.Monetary(
        string="Price per m2",
        required=False,
        currency_field='currency_id',
        tracking=True,
    )
    floor_price_range_ids = fields.One2many(
        'floor.price.range',
        'site_id',
        string='Floor Price Ranges',
    )
    has_full_floor_price_coverage = fields.Boolean(
        compute='_compute_has_full_floor_price_coverage',
        string='All floors priced',
        store=True,
    )

    @api.depends('floor_price_range_ids.floor_from_id', 'floor_price_range_ids.floor_to_id', 'floor_price_range_ids.price')
    def _compute_has_full_floor_price_coverage(self):
        """True when all used floors of this site have a price range."""
        Property = self.env['property.property']
        for site in self:
            props = Property.search([('site', '=', site.id)])
            floors = props.mapped('floor_id')
            if not floors:
                site.has_full_floor_price_coverage = False
                continue

            ranges = site.floor_price_range_ids

            def _is_floor_covered(floor):
                n_floor = _floor_name_to_number(floor.name)
                if n_floor is None:
                    return False
                for r in ranges:
                    if not r.floor_from_id or not r.floor_to_id or not r.price:
                        continue
                    n_from = _floor_name_to_number(r.floor_from_id.name)
                    n_to = _floor_name_to_number(r.floor_to_id.name)
                    if n_from is not None and n_to is not None and n_from <= n_floor <= n_to:
                        return True
                return False

            site.has_full_floor_price_coverage = all(
                _is_floor_covered(f) for f in floors
            )
