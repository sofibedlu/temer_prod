# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    entry_custom_checklist_ids = fields.Many2many(
        "employee.entry.custom.checklist", string="Entry Checklist")
    exit_custom_checklist_ids = fields.Many2many(
        "employee.exit.custom.checklist", string="Exit Checklist")

    entry_custom_checklist = fields.Float(
        " Checklist Completed", compute="_compute_entry_custom_checklist")
    exit_custom_checklist = fields.Float(
        " Checklist Completed ", compute="_compute_exit_custom_checklist")
