from odoo import models, fields, api

class SiteDeveloper(models.Model):
    _name = 'site.developer'
    _description = 'Developer'

    name = fields.Char(string='Name')
    sequence = fields.Many2one('ir.sequence', string='Sequence')