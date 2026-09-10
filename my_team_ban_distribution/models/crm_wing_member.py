# -*- coding: utf-8 -*-
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class CrmWingMember(models.Model):
    _inherit = "crm.wing.member"

    def _deactivate_distribution_for_users(self, users):
        """Set active=False on all distribution rows for the given users."""
        users = users.exists()
        if not users:
            return self.env["crm.wing.member"]

        members = self.sudo().with_context(active_test=False).search(
            [("user_id", "in", users.ids), ("active", "=", True)]
        )
        if members:
            members.write({"active": False})
            _logger.info(
                "Distribution Configuration: deactivated %s row(s) for user(s) %s",
                len(members),
                ", ".join(users.mapped("name")),
            )
        return members
