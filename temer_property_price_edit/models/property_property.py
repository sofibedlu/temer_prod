# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Property(models.Model):
    _inherit = "property.property"

    use_manual_sale_price = fields.Boolean(
        string="Use manual sales price",
        default=False,
        store=True,
        help="When set, the Sales Price is taken from the manually entered value instead of the calculated one.",
    )

    unit_price = fields.Monetary(inverse="_inverse_unit_price")

    def _inverse_unit_price(self):
        """When user edits Sales Price in the form, keep that value (do not overwrite with calculated)."""
        for rec in self:
            rec.use_manual_sale_price = True
            rec.manual_unit_price = rec.unit_price

    @api.depends(
        "use_manual_sale_price",
        "manual_unit_price",
        "site",
        "site.is_fixed_price",
        "gross_area",
        "sale_rent",
        "price",
    )
    def compute_total_price(self):
        for rec in self:
            if rec.use_manual_sale_price:
                rec.unit_price = rec.manual_unit_price or 0.0
                if rec.sale_rent == "for_sale":
                    rec.rent_month = 0.0
                elif rec.sale_rent == "for_tenancy":
                    rec.rent_month = (rec.price or 0.0) * (rec.gross_area or 0.0)
                else:
                    rec.rent_month = 0.0
            elif rec.site and rec.site.is_fixed_price:
                rec.unit_price = rec.manual_unit_price or 0.0
                rec.rent_month = 0.0
            else:
                if rec.sale_rent == "for_sale":
                    rec.unit_price = (rec.price or 0.0) * (rec.gross_area or 0.0)
                    rec.rent_month = 0.0
                elif rec.sale_rent == "for_tenancy":
                    rec.unit_price = 0.0
                    rec.rent_month = (rec.price or 0.0) * (rec.gross_area or 0.0)
                else:
                    rec.unit_price = 0.0
                    rec.rent_month = 0.0
