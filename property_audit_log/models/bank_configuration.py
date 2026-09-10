# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.osv import expression


class BankConfigurationSearch(models.Model):
    _inherit = 'bank.configuration'

    # Search by bank name / account (rec_name is computed — not searchable)
    _rec_names_search = ['bank', 'bank_ethiopian.name', 'account_number']

    def _bank_name_search_domain(self, name, operator='ilike'):
        name = (name or '').strip()
        if not name:
            return []
        return [
            '|', '|',
            ('bank', operator, name),
            ('bank_ethiopian.name', operator, name),
            ('account_number', operator, name),
        ]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = list(args or [])
        if name:
            domain = expression.AND([self._bank_name_search_domain(name, operator), domain])
        records = self.search(domain, limit=limit)
        return [(r.id, r.display_name) for r in records]

    @api.depends('bank', 'bank_ethiopian', 'account_number')
    def _compute_display_name(self):
        for rec in self:
            bank_name = rec.bank_ethiopian.name if rec.bank_ethiopian else ''
            if not bank_name and rec.bank:
                bank_name = (rec.bank.split(' - ')[0] or rec.bank).strip()
            parts = [p for p in (bank_name, rec.account_number) if p]
            rec.display_name = ' - '.join(parts) if parts else (rec.bank or _('Bank'))

    def name_get(self):
        return [(r.id, r.display_name) for r in self]
