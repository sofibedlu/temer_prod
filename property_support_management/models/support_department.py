from odoo import models, fields

class SupportDepartment(models.Model):
    _name = 'support.department'
    _description = 'Support Department'
    _order = 'name'

    name = fields.Char(string='Department Name', required=True)
    color = fields.Integer('Color Index', default=0)
