# -*- coding: utf-8 -*-
from odoo import models


class MyTeamMember(models.Model):
    _inherit = "my.team.member"

    def action_ban_user(self):
        banned_user = self.user_id
        result = super().action_ban_user()
        if banned_user:
            self.env["crm.wing.member"]._deactivate_distribution_for_users(
                banned_user
            )
        return result
