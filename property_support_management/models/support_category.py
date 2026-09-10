from odoo import models, fields

class SupportCategory(models.Model):
    _name = 'support.category'
    _description = 'Support Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
