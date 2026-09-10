from odoo import models, fields


class LetterTypePrefix(models.Model):
    _name = 'letter.type.prefix'
    _description = 'Letter Type Prefix'
    _rec_name = 'letter_type_id'
    _order = 'letter_type_id'

    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        required=True,
        ondelete='cascade',
    )
    prefix = fields.Char(
        string='Prefix',
        required=True,
        help="Short code placed before the letter number. Example: DL",
    )

    _sql_constraints = [
        ('letter_type_uniq', 'unique(letter_type_id)',
         'A prefix already exists for this Letter Type.'),
    ]
