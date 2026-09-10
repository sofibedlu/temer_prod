from odoo import models, fields


class CollectionOrderInherit(models.Model):
    _inherit = 'collection.order'

    letter_ids = fields.One2many(
        'letter.saved',
        'collection_id',
        string='Saved Letters',
    )
    request_letter_count = fields.Integer(string='Requests', compute='_compute_letter_counts')
    penalty_letter_count = fields.Integer(string='Penalties', compute='_compute_letter_counts')
    termination_letter_count = fields.Integer(string='Terminations', compute='_compute_letter_counts')
    other_letter_count = fields.Integer(string='Others', compute='_compute_letter_counts')

    def _compute_letter_counts(self):
        for rec in self:
            req = pen = term = oth = 0
            for letter in rec.letter_ids:
                type_name = letter.letter_type_id.name.lower() if getattr(letter, 'letter_type_id', False) else ''
                if 'request' in type_name:
                    req += 1
                elif 'penal' in type_name:
                    pen += 1
                elif 'terminat' in type_name:
                    term += 1
                else:
                    oth += 1
            
            rec.request_letter_count = req
            rec.penalty_letter_count = pen
            rec.termination_letter_count = term
            rec.other_letter_count = oth

    def _action_open_letters_by_domain(self, name, type_domain):
        self.ensure_one()
        domain = [('collection_id', '=', self.id)]
        if type_domain:
            domain.append(type_domain)
            
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'letter.saved',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'default_collection_id': self.id},
        }

    def action_open_request_letters(self):
        return self._action_open_letters_by_domain('Request Letters', ('letter_type_id.name', 'ilike', 'request'))

    def action_open_penalty_letters(self):
        return self._action_open_letters_by_domain('Penalty Letters', ('letter_type_id.name', 'ilike', 'penal'))

    def action_open_termination_letters(self):
        return self._action_open_letters_by_domain('Termination Letters', ('letter_type_id.name', 'ilike', 'terminat'))

    def action_open_other_letters(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Other Letters',
            'res_model': 'letter.saved',
            'view_mode': 'tree,form',
            'domain': [
                ('collection_id', '=', self.id),
                '!', ('letter_type_id.name', 'ilike', 'request'),
                '!', ('letter_type_id.name', 'ilike', 'penal'),
                '!', ('letter_type_id.name', 'ilike', 'terminat'),
            ],
            'context': {'default_collection_id': self.id},
        }
