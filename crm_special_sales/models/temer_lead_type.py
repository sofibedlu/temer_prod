# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api


def _name_to_code(name):
    """Generate a valid code from a type name (lowercase, alphanumeric + underscore)."""
    return re.sub(r'[^a-z0-9]+', '_', (name or '').lower()).strip('_') or 'other'


class TemerLeadType(models.Model):
    _name = 'temer.lead.type'
    _description = 'Special Sales Lead Type'
    _order = 'sequence, id'

    name = fields.Char('Type', required=True, translate=True)
    code = fields.Char('Code', required=True, size=64,
                       help='Internal code (e.g. employee = Contact, others = Customer name). Auto-filled from name if empty.')
    sequence = fields.Integer(default=10)

    @api.onchange('name')
    def _onchange_name_code(self):
        """Suggest code from name when creating a new type."""
        if self.name and not self.code:
            self.code = _name_to_code(self.name)

    @api.model
    def create(self, vals):
        if vals.get('name') and not vals.get('code'):
            vals = dict(vals)
            vals['code'] = _name_to_code(vals['name'])
        return super().create(vals)
