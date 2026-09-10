# -*- coding: utf-8 -*-
"""
Shared watermark utilities for contract_draft_status.
Used by docx_watermark.py.
"""
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)


def show_watermark(sale):
    """Return True only when draft_status == 'draft'."""
    draft = (
        request.env["draft.contract.archive"].search(
            [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
        )
        or request.env["draft.contract.archive"].search(
            [("source_archive_id.sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
        )
    )
    if not draft:
        return False
    result = (draft.draft_status == "draft")
    _logger.info(
        "watermark check: sale=%s draft_status=%s show=%s",
        sale.name, draft.draft_status, result,
    )
    return result
