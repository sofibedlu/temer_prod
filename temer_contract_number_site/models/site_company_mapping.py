import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SiteCompanyMapping(models.Model):
    _name = "site.company.mapping"
    _description = "Company Site Mapping"
    _rec_name = "company_id"

    company_id = fields.Many2one("site.company", string="Company", required=True)
    line_ids = fields.One2many(
        "site.company.mapping.line",
        "mapping_id",
        string="Sites",
    )

    _sql_constraints = [
        (
            "unique_company_mapping",
            "unique(company_id)",
            "Each company can only have one Company Site Mapping record.",
        ),
    ]


class SiteCompanyMappingLine(models.Model):
    _name = "site.company.mapping.line"
    _description = "Company Site Mapping Line"
    _rec_name = "display_name"

    mapping_id = fields.Many2one(
        "site.company.mapping",
        string="Mapping",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "site.company",
        related="mapping_id.company_id",
        store=True,
        readonly=True,
    )
    location_id = fields.Many2one("site.location", string="Location", required=True)
    site_id = fields.Many2one("property.site", string="Site", required=True)
    site_abbreviation = fields.Char(string="Site Abbreviation", required=True)
    display_name = fields.Char(
        string="Name",
        compute="_compute_display_name",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_site_mapping",
            "unique(site_id)",
            "A site can only be mapped to one company.",
        ),
    ]

    @api.depends("company_id", "location_id", "site_id", "site_abbreviation")
    def _compute_display_name(self):
        for rec in self:
            company = rec.company_id.name or ""
            location = rec.location_id.name or ""
            site = rec.site_id.name or ""
            abbr = rec.site_abbreviation or ""
            rec.display_name = f"{company} - {location} - {site} [{abbr}]"

    def _normalize_site_abbreviation(self, value):
        return re.sub(r"[^A-Za-z0-9]", "", (value or "").upper())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("site_abbreviation"):
                vals["site_abbreviation"] = self._normalize_site_abbreviation(
                    vals["site_abbreviation"]
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("site_abbreviation"):
            vals["site_abbreviation"] = self._normalize_site_abbreviation(
                vals["site_abbreviation"]
            )
        return super().write(vals)

    @api.constrains("site_abbreviation")
    def _check_site_abbreviation(self):
        for rec in self:
            if not rec.site_abbreviation:
                raise ValidationError(_("Site abbreviation is required."))