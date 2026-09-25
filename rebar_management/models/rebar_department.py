from odoo import fields, models

class RebarDepartment(models.Model):
    _name = 'rebar.department'
    _description = 'Rebar Requesting Department'

    name = fields.Char(string='Department Name', required=True, index=True)
    active = fields.Boolean(default=True)