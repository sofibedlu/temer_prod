# -*- coding: utf-8 -*-

from odoo import models


class TemerLead(models.Model):
    _inherit = 'temer.lead'

    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Search by customer name, lead name, phone numbers, notes; supports Amharic (UTF-8)."""
        args = args or []
        if name and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = [
                '|', '|', '|', '|', '|', '|', '|', '|',
                ('customer_name', operator, name),
                ('name', operator, name),
                ('phone_no', operator, name),
                ('phone_ids.phone', operator, name),
                ('additional_numbers_ids.number', operator, name),
                ('site_ids.name', operator, name),
                ('notes', operator, name),
                ('partner_id.name', operator, name),
            ]
            leads = self._search(domain + args, limit=limit, order=order or self._order)
            if leads.ids:
                return leads.ids
        return super()._name_search(name=name, args=args, operator=operator, limit=limit, order=order)
