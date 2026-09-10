# -*- coding: utf-8 -*-
# Make site_id optional: allow NULL on collection_plan_stage.site_id

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    try:
        cr.execute("""
            ALTER TABLE collection_plan_stage
            ALTER COLUMN site_id DROP NOT NULL
        """)
        _logger.info("collection_plan_stage.site_id: dropped NOT NULL")
    except Exception as e:
        _logger.warning("collection_plan_stage.site_id migration: %s", e)
