# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PropertyPropertyFinishingRate(models.Model):
    _inherit = 'property.property'

    rate_per_m2 = fields.Float(
        string="Rate-m²",
        help="Rate per square meter added on top of base price for fully finished properties",
    )

    commercial_amount = fields.Float(
        string="Commercial Amount",
        help="Additional amount for commercial properties used as reservation advance base",
    )

    @api.depends('rate_per_m2', 'finishing', 'price', 'gross_area', 'sale_rent', 'site')
    def compute_total_price(self):
        for rec in self:
            if rec.finishing == 'fully_finished' and rec.rate_per_m2 and rec.sale_rent == 'for_sale':
                gross_area = rec.gross_area or 0.0
                new_price = ((rec.price or 0.0) * gross_area) + (rec.rate_per_m2 * gross_area)
                if 'manual_unit_price' in rec._fields:
                    rec.manual_unit_price = new_price
                    rec.use_manual_sale_price = True
                super(PropertyPropertyFinishingRate, rec).compute_total_price()
            else:
                # Clear manual override so base price recalculates normally
                if 'use_manual_sale_price' in rec._fields:
                    rec.use_manual_sale_price = False
                    rec.manual_unit_price = 0.0
                super(PropertyPropertyFinishingRate, rec).compute_total_price()
