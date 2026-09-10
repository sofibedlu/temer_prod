# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmSpecialSalesCompany(models.Model):
    _name = 'crm.special.sales.company'
    _description = 'Special Sales Company'
    _order = 'name'

    name = fields.Char('Company Name', required=True, translate=True)
