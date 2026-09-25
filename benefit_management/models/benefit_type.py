from odoo import models, fields

class BenefitType(models.Model):
    _name = 'benefit.type'
    _description = 'Benefit Type Configuration'
    _order = 'name'

    name = fields.Char(string='Benefit Name', required=True, translate=True)
    code = fields.Char(string='Code', copy=False)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)