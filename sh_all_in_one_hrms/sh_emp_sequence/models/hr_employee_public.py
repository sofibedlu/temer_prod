# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    emp_no = fields.Char(string='Employee No.')
