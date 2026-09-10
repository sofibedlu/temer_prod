# -*- coding: utf-8 -*-
"""Fix stale actions that still point to removed model crm.special.sales."""


def post_init_hook(env):
    """After install/upgrade: fix any action that still uses crm.special.sales,
    and populate crm.employee.ref from hr.employee."""
    actions = env['ir.actions.act_window'].search([('res_model', '=', 'crm.special.sales')])
    if actions:
        view = env.ref('crm_special_sales.view_temer_lead_form_special_sales', raise_if_not_found=False)
        vals = {
            'res_model': 'temer.lead',
            'view_mode': 'tree,form',
            'domain': "[('from_special_sales', '=', True)]",
            'context': "{'default_from_special_sales': True}",
            'view_id': view.id if view else False,
        }
        actions.write(vals)

    # Populate employee reference table
    env['crm.employee.ref'].sync_from_hr()
