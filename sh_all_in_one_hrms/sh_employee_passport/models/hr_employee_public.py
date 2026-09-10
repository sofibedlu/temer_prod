# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    sh_employee_passport_ids = fields.One2many(
        "sh.employee.passport",
        "employee_id",
        string="Passport Line")
    state = fields.Selection([("draft", "New"),
                              ("progress", "Under Progress"),
                              ("approved", "Approved"),
                              ("cancelled", "Cancelled"),
                              ("expired", "Expired")],
                             string="Status",
                             compute="_compute_state")
