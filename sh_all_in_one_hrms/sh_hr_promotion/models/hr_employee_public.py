# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    employee_promotion_ids = fields.One2many(
        'sh.hr.promotion', 'employee_id', string='Promotion Line', copy=True, auto_join=True)
    pr_count = fields.Integer(
        'Promotions Count', compute='_compute_get_hr_count')
