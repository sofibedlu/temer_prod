# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from odoo import fields, models

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"
    _check_company_auto = True

    entry_checklist_ids = fields.Many2many(
        "employee.entry.checklist",
        string="Entry Checklist")
    exit_checklist_ids = fields.Many2many(
        "employee.exit.checklist",
        string="Exit Checklist")

    entry_checklist = fields.Float(
        "Checklist Completed",
        compute="_compute_entry_checklist")
    exit_checklist = fields.Float(
        "Checklist Completed ",
        compute="_compute_exit_checklist")
