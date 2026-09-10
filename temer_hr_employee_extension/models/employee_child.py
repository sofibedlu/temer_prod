from odoo import models, fields


class EmployeeChild(models.Model):
    _name = 'employee.child'
    _description = 'Employee Child Information'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        ondelete='cascade',
        required=True
    )
    name = fields.Char(string="Child Name", required=True)
    birth_date = fields.Date(string="Birth Date")
    place_of_birth = fields.Char(string="Place of Birth")
