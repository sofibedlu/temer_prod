# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    document_count = fields.Integer(
        'Documents', compute='_compute_document_count')
