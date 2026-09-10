# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmTeamRotation(models.Model):
    _name = "crm.team.rotation"
    _description = "CRM Team Rotation"

    team_id = fields.Many2one(
        "property.sales.wing",
        string="Team",
        required=True,
        ondelete="cascade",
    )
    type = fields.Selection(
        selection=[
            ("walkin", "Walkin"),
            ("call_center", "Call Center"),
            ("website", "Website"),
        ],
        required=True,
    )
    last_user_id = fields.Many2one("res.users", ondelete="set null")
    last_assigned_at = fields.Datetime()

    _sql_constraints = [
        (
            "unique_team_type_rotation",
            "unique(team_id, type)",
            "Rotation state already exists for this team and type.",
        ),
    ]
