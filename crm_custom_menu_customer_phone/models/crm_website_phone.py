# -*- coding: utf-8 -*-

from odoo import fields, models


class CrmWebsitePhoneCountry(models.Model):
    _inherit = "crm.website.phone"

    country_id = fields.Many2one("res.country", string="Country", ondelete="set null")
