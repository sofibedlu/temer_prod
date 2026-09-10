# -*- coding: utf-8 -*-
"""Backfill company_id and freelance_id from customer_name for existing Special Sales leads."""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Lead = env['temer.lead']
        leads = Lead.search([
            ('from_special_sales', '=', True),
            ('customer_name', '!=', False),
        ])
        updated = 0
        for lead in leads:
            code = lead.lead_type_id.code if lead.lead_type_id else (lead.lead_type or '')
            if code == 'company' and not lead.company_id and lead.customer_name:
                company = env['crm.special.sales.company'].search([
                    ('name', '=ilike', lead.customer_name.strip())
                ], limit=1)
                if not company:
                    company = env['crm.special.sales.company'].create({'name': lead.customer_name.strip()})
                lead.company_id = company
                updated += 1
            elif code == 'freelance' and not lead.freelance_id and lead.customer_name:
                freelance = env['crm.special.sales.freelance'].search([
                    ('name', '=ilike', lead.customer_name.strip())
                ], limit=1)
                if not freelance:
                    freelance = env['crm.special.sales.freelance'].create({'name': lead.customer_name.strip()})
                lead.freelance_id = freelance
                updated += 1
        if updated:
            _logger.info("crm_special_sales: Backfilled company_id/freelance_id for %s lead(s)", updated)
    except Exception as e:
        _logger.warning("crm_special_sales migration 17.0.1.0.4: %s", e)
