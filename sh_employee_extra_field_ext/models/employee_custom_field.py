from odoo import models, fields

class Employee(models.Model):
    _inherit = 'hr.employee'

    account_number = fields.Char(string='Account Number')
    tax_id = fields.Char(string='Tax ID')