# -*- coding: utf-8 -*-
import json
import urllib.parse
import uuid

from odoo.osv import expression

# States from confirm onward in the property sale workflow.
SALES_DEAL_CLOSED_STATES = ['confirm', 'audit', 'approve', 'done']
SALES_DEAL_CLOSED_DOMAIN = [('state', 'in', SALES_DEAL_CLOSED_STATES)]
EXPORT_TOKEN_PARAM_PREFIX = 'temer_sales_report.export.'


def temer_export_act_url(records, route, base_domain):
    """Build act_url for Excel export: selected rows, or all rows matching list filters."""
    if records.ids:
        record_ids = list(records.ids)
    else:
        active_domain = records.env.context.get('active_domain') or []
        domain = expression.AND([list(base_domain), active_domain])
        record_ids = records.env[records._name].search(domain).ids

    token = uuid.uuid4().hex
    key = '%s%s.%s' % (EXPORT_TOKEN_PARAM_PREFIX, records.env.uid, token)
    records.env['ir.config_parameter'].sudo().set_param(
        key,
        json.dumps({
            'model': records._name,
            'ids': record_ids,
        }),
    )
    query = urllib.parse.urlencode({'token': token})
    return {
        'type': 'ir.actions.act_url',
        'url': '/temer_sales_report/export/%s?%s' % (route, query),
        'target': 'self',
    }
