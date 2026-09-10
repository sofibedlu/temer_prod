from odoo import fields, models

class CollectionProgressShiftConfig(models.Model):
    _name = "collection.progress.shift.config"
    _description = "Construction Progress Due Date Shift Config"
    _rec_name = "site_id"

    site_id = fields.Many2one(
        "property.site",
        string="Site",
        required=True,
        ondelete="cascade",
        index=True,
    )
    enabled = fields.Boolean(
        string="Enable Due Date Shift from Progress",
        default=True,
        help="If disabled, completing construction progress will NOT set/shift due dates for this site.",
    )
    shift_days = fields.Integer(
        string="Shift Days",
        default=30,
        help="Number of days to add when progress is completed (only if enabled).",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("uniq_site", "unique(site_id)", "A configuration already exists for this site."),
    ]