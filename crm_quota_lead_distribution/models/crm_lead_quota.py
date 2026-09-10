# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLeadQuota(models.Model):
    _name = "crm.lead.quota"
    _description = "CRM Lead Quota"
    _rec_name = "display_name"
    _order = "team_id, type"

    team_id = fields.Many2one(
        "property.sales.wing",
        string="Team",
        required=True,
        ondelete="restrict",
    )
    quota = fields.Integer(string="Quota", required=True, default=0)
    assigned_count = fields.Integer(
        string="Assigned",
        default=0,
        readonly=True,
    )
    remaining = fields.Integer(
        string="Remaining",
        compute="_compute_remaining",
        store=True,
    )
    type = fields.Selection(
        selection=[
            ("walkin", "Walkin"),
            ("call_center", "Call Center"),
            ("website", "Website"),
        ],
        string="Type",
        required=True,
    )
    active = fields.Boolean(string="Active", default=True)

    display_name = fields.Char(compute="_compute_display_name", store=True)
    ratio = fields.Float(
        string="Ratio",
        compute="_compute_ratio",
        store=True,
        digits=(16, 4),
        help="Remaining / Quota — higher ratio gets the next lead.",
    )

    _sql_constraints = [
        (
            "unique_team_type",
            "unique(team_id, type)",
            "Quota already exists for this Team and Type.",
        ),
    ]

    @api.depends("team_id", "type")
    def _compute_display_name(self):
        type_labels = dict(self._fields["type"].selection)
        for rec in self:
            wing = rec.team_id.name or ""
            channel = type_labels.get(rec.type, "")
            rec.display_name = (
                f"{wing} - {channel}" if wing or channel else "Lead Quota"
            )

    @api.depends("quota", "assigned_count")
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = (rec.quota or 0) - (rec.assigned_count or 0)

    @api.depends("quota", "assigned_count", "remaining")
    def _compute_ratio(self):
        for rec in self:
            if rec.quota:
                rec.ratio = (rec.remaining or 0) / float(rec.quota)
            else:
                rec.ratio = 0.0

    def action_reset_quota(self):
        self.write({"assigned_count": 0})
