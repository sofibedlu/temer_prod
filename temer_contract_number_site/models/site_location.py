import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SiteLocation(models.Model):
    _name = "site.location"
    _description = "Site Location"
    _rec_name = "name"

    name = fields.Char(string="Location Name", required=True)
    abbreviation = fields.Char(string="Abbreviation", required=True)
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True
    )

    _sql_constraints = [
        ("unique_location_name", "unique(name)", "The location name must be unique."),
    ]

    @api.depends("name", "abbreviation")
    def _compute_display_name(self):
        for rec in self:
            if rec.abbreviation:
                rec.display_name = f"[{rec.abbreviation}] {rec.name}"
            else:
                rec.display_name = rec.name

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []

        domain = ['|', ('name', operator, name), ('abbreviation', operator, name)]
        domain = args + domain

        records = self.search(domain, limit=limit)
        return records.name_get()

    def _normalize_abbreviation(self, value):
        return re.sub(r"[^A-Za-z0-9]", "", (value or "").upper())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("abbreviation"):
                vals["abbreviation"] = self._normalize_abbreviation(vals["abbreviation"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("abbreviation"):
            vals["abbreviation"] = self._normalize_abbreviation(vals["abbreviation"])
        return super().write(vals)

    @api.constrains("abbreviation")
    def _check_abbreviation(self):
        for rec in self:
            if not rec.abbreviation:
                raise ValidationError(_("Location abbreviation is required."))