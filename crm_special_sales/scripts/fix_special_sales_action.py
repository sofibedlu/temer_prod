#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time fix: update any ir.actions.act_window with res_model='crm.special.sales' to temer.lead.
Run from Odoo root with: python odoo-bin shell -d YOUR_DATABASE_NAME
Then in the shell:
    exec(open('odoo/addons-production/crm_special_sales/scripts/fix_special_sales_action.py').read())
Or run as standalone script (requires env):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    ... (paste the fix block below)
"""
# Paste this in Odoo shell (python odoo-bin shell -d trremer390):
#
# env = env  # shell provides env
# actions = env['ir.actions.act_window'].search([('res_model', '=', 'crm.special.sales')])
# if actions:
#     view = env.ref('crm_special_sales.view_temer_lead_form_special_sales', raise_if_not_found=False)
#     search_view = env.ref('temer_crm.view_temer_lead_search', raise_if_not_found=False)
#     actions.write({
#         'res_model': 'temer.lead',
#         'view_mode': 'tree,form',
#         'domain': "[('from_special_sales', '=', True)]",
#         'context': "{'default_from_special_sales': True, 'default_lead_type': 'company'}",
#         'view_id': view.id if view else False,
#         'search_view_id': search_view.id if search_view else False,
#     })
#     print('Updated %s action(s)' % len(actions))
# else:
#     print('No stale crm.special.sales actions found')
