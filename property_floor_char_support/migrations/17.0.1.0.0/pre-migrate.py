# -*- coding: utf-8 -*-
"""Migrate property_floor.name from Integer to VARCHAR for character support."""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Convert name column from integer to varchar to allow letters and special chars."""
    # Drop floor_name if exists (removed from previous version)
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'property_floor' AND column_name = 'floor_name'
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE property_floor DROP COLUMN floor_name")
        _logger.info("Dropped property_floor.floor_name column")
    # Convert name from integer to varchar
    cr.execute("""
        ALTER TABLE property_floor
        ALTER COLUMN name TYPE varchar USING name::text
    """)
    _logger.info("Migrated property_floor.name from integer to varchar")
