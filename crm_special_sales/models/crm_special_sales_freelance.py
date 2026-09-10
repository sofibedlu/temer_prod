# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmSpecialSalesFreelance(models.Model):
    _name = 'crm.special.sales.freelance'
    _description = 'Special Sales Freelance'
    _order = 'name'

    name = fields.Char('Freelance Name', required=True, translate=True)
