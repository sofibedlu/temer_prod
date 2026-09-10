# -*- coding: utf-8 -*-
"""Fix actions that still point to removed model crm.special.sales (upgrade from 17.0.1.0.0)."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    actions = env['ir.actions.act_window'].search([('res_model', '=', 'crm.special.sales')])
    if not actions:
        return
    view = env.ref('crm_special_sales.view_temer_lead_form_special_sales', raise_if_not_found=False)
    vals = {
        'res_model': 'temer.lead',
        'view_mode': 'tree,form',
        'domain': "[('from_special_sales', '=', True)]",
        'context': "{'default_from_special_sales': True, 'default_lead_type': 'company'}",
        'view_id': view.id if view else False,
    }
    actions.write(vals)
