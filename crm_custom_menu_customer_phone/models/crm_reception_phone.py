# -*- coding: utf-8 -*-

from odoo import fields, models


class CrmReceptionPhoneCountry(models.Model):
    _inherit = "crm.reception.phone"

    country_id = fields.Many2one("res.country", string="Country", ondelete="set null")
