# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active") is False:
            self.env["crm.wing.member"]._deactivate_distribution_for_users(self)
        return res
