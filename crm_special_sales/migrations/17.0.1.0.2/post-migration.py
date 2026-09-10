# -*- coding: utf-8 -*-
"""Fix any actions that still point to removed model crm.special.sales."""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        actions = env['ir.actions.act_window'].search([('res_model', '=', 'crm.special.sales')])
        if not actions:
            return
        view = env.ref('crm_special_sales.view_temer_lead_form_special_sales', raise_if_not_found=False)
        search_view = env.ref('temer_crm.view_temer_lead_search', raise_if_not_found=False)
        vals = {
            'res_model': 'temer.lead',
            'view_mode': 'tree,form',
            'domain': "[('from_special_sales', '=', True)]",
            'context': "{'default_from_special_sales': True, 'default_lead_type': 'company'}",
            'view_id': view.id if view else False,
            'search_view_id': search_view.id if search_view else False,
        }
        actions.write(vals)
        _logger.info("crm_special_sales: Updated %s action(s) from crm.special.sales to temer.lead", len(actions))
    except Exception as e:
        _logger.warning("crm_special_sales migration 17.0.1.0.2: %s", e)
