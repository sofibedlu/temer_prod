# -*- coding: utf-8 -*-
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        fixed = env['property.property']._fix_buggy_computed_references()
        _logger.info(
            'property_reference_floor_id 17.0.1.0.1: upgrade corrected %s reference(s).',
            fixed,
        )
    except Exception:
        _logger.exception('property_reference_floor_id: upgrade fix failed.')
