# -*- coding: utf-8 -*-
"""
Stub model so old menus/actions that still point to crm.special.sales do not crash.
Real Special Sales is temer.lead (TEMER CRM > Special Sales).
"""
from odoo import models, fields, _


class CrmSpecialSalesStub(models.Model):
    _name = 'crm.special.sales'
    _description = 'Special Sales (legacy stub – use TEMER CRM > Special Sales)'

    name = fields.Char(default='Special Sales', required=True)
    create_date = fields.Datetime(string='Created on', readonly=True)

    def action_open_temer_special_sales(self):
        """Open the real Special Sales (temer.lead with from_special_sales)."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Special Sales'),
            'res_model': 'temer.lead',
            'view_mode': 'tree,form',
            'domain': [('from_special_sales', '=', True)],
            'context': {'default_from_special_sales': True},
        }
