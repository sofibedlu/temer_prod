from odoo import models, fields


class LetterType(models.Model):
    """
    Configurable letter type — replaces the hardcoded Selection field.
    Users can add, rename, or deactivate types without code changes.
    """
    _name = 'letter.type'
    _description = 'Letter Type'
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char(string='Letter Type', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    # ── Back-references ───────────────────────────────────────────────────────
    template_ids = fields.One2many(
        'letter.template', 'letter_type_id',
        string='Templates',
        readonly=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Letter Type name must be unique.'),
    ]
