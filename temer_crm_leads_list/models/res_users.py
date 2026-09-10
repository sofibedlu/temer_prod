# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        res = super().write(vals)
        if 'groups_id' in vals and self:
            # Notify each modified user so their session reloads and menu updates
            for user in self:
                if user.partner_id:
                    self.env['bus.bus']._sendone(
                        user.partner_id,
                        'res_users_groups_updated',
                        {},
                    )
        return res
