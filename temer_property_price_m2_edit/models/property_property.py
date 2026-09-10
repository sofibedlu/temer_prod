from odoo import api, fields, models


class Property(models.Model):
    """
    - `override_price_m2` is what the user edits.
    - When set, `price` is set from it and Sales Price (unit_price) is recalculated
      from price * gross_area (and rent_month for tenancy).
    """

    _inherit = "property.property"

    override_price_m2 = fields.Float(
        string="Price(m2)",
        help="Manual Price(m2) override. When set, it is used and Sales Price is recalculated.",
    )

    @api.depends(
        "override_price_m2",
        "site",
        "payment_structure_id",
        "site_payment_structure_id",
        "floor_id",
        "floor_ids",
    )
    def compute_unit_price(self):
        manual_recs = self.filtered(lambda r: bool(r.override_price_m2))
        auto_recs = self - manual_recs

        if auto_recs:
            super(Property, auto_recs).compute_unit_price()

        for rec in manual_recs:
            rec.price = rec.override_price_m2

    @api.depends("override_price_m2", "price", "gross_area", "sale_rent")
    def compute_total_price(self):
        """When override_price_m2 is set, always recalc Sales Price from price * gross_area."""
        with_override = self.filtered(lambda r: bool(r.override_price_m2))
        others = self - with_override

        if others:
            super(Property, others).compute_total_price()

        for rec in with_override:
            if rec.sale_rent == "for_sale":
                rec.unit_price = (rec.price or 0.0) * (rec.gross_area or 0.0)
                rec.rent_month = 0.0
            elif rec.sale_rent == "for_tenancy":
                rec.unit_price = 0.0
                rec.rent_month = (rec.price or 0.0) * (rec.gross_area or 0.0)
            else:
                rec.unit_price = 0.0
                rec.rent_month = 0.0

