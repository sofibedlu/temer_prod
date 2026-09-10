# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmEmployeeRef(models.Model):
    """Lightweight proxy of hr.employee — only id + name.
    Populated via sudo so no restricted-field access errors on mobile."""
    _name = 'crm.employee.ref'
    _description = 'Employee Reference (CRM)'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Full Name', required=True)
    hr_employee_id = fields.Integer('HR Employee ID', index=True)

    @api.model
    def sync_from_hr(self):
        """Sync all active employees from hr.employee using sudo."""
        employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
        existing = {r.hr_employee_id: r for r in self.search([])}
        for emp in employees:
            if emp.id in existing:
                if existing[emp.id].name != emp.name:
                    existing[emp.id].name = emp.name
            else:
                self.create({'name': emp.name, 'hr_employee_id': emp.id})
        # Remove refs for deleted/archived employees
        active_ids = employees.mapped('id')
        to_remove = self.search([('hr_employee_id', 'not in', active_ids)])
        to_remove.unlink()
