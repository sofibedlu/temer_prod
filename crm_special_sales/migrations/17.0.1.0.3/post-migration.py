# -*- coding: utf-8 -*-
"""Backfill lead_type_id from legacy lead_type (Selection) for existing Special Sales leads."""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Lead = env['temer.lead']
        Type = env['temer.lead.type']
        types_by_code = {t.code: t for t in Type.search([])}
        leads = Lead.search([
            ('from_special_sales', '=', True),
            ('lead_type_id', '=', False),
            ('lead_type', 'in', ['company', 'freelance', 'employee']),
        ])
        for lead in leads:
            lt = types_by_code.get(lead.lead_type)
            if lt:
                lead.lead_type_id = lt
        if leads:
            _logger.info("crm_special_sales: Backfilled lead_type_id for %s Special Sales lead(s)", len(leads))
    except Exception as e:
        _logger.warning("crm_special_sales migration 17.0.1.0.3: %s", e)
