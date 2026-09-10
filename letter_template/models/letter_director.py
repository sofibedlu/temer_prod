from odoo import models, fields


class LetterDirector(models.Model):
    _name = 'letter.director'
    _description = 'Letter Director'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Director Name', required=True)
    active = fields.Boolean(default=True)
