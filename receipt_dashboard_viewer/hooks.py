# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    records = env['receipt.approval.record'].search([])
    if records:
        records._compute_site_company_id()
        _logger.info(
            'receipt_dashboard_viewer: backfilled site_company_id on %d record(s).',
            len(records),
        )
