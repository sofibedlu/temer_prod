# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    try:
        fixed = env['property.property']._fix_buggy_computed_references()
        _logger.info(
            'property_reference_floor_id: install corrected %s reference(s).',
            fixed,
        )
    except Exception:
        _logger.exception(
            'property_reference_floor_id: install fix skipped (module still loads).'
        )
