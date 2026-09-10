from odoo import models, fields


class EmployeeAsset(models.Model):
    _name = 'employee.asset'
    _description = 'Employee Company Asset'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        ondelete='cascade',
        required=True
    )
    asset_type = fields.Selection([
        ('vehicle', 'VEHICLE'),
        ('laptop_desktop', 'Laptop / Desktop'),
        ('mobile_phone', 'MOBILE PHONE'),
        ('sim_card', 'SIM CARD'),
        ('other', 'OTHERS'),
    ], string="Asset Type", required=True)
    reference = fields.Char(string="Reference (Plate/Serial/Number)")
    other_description = fields.Char(string="Other Description")
