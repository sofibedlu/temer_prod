# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, api


class ShMessageWizard(models.TransientModel):
    _name = "sh.message.wizard"
    _description = "Message wizard to display warnings, alert ,success messages"

    @api.model
    def _default_name(self):
        return self.env.context.get('message', False)

    name = fields.Text(string="Message", readonly=True, default=_default_name)
