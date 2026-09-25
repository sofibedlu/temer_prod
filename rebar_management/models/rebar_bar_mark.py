from odoo import fields, models

class RebarBarMark(models.Model):
    _name = 'rebar.bar.mark'
    _description = 'Rebar Bar Mark Specification'

    name = fields.Char(string='Bar Mark Code', required=True, index=True)
    description = fields.Char(string='Description / Structural Member')
    active = fields.Boolean(default=True)