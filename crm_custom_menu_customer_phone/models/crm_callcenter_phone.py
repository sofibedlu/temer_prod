# -*- coding: utf-8 -*-

from odoo import models, fields


class CrmCallCenterPhoneCountry(models.Model):
    _inherit = 'crm.callcenter.phone'

    country_id = fields.Many2one('res.country', string="Country", ondelete='set null')
