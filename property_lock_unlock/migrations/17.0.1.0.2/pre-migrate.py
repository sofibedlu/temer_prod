# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE property_property
            ADD COLUMN IF NOT EXISTS lock_on_expire_by_id INTEGER,
            ADD COLUMN IF NOT EXISTS lock_on_expire_date TIMESTAMP WITHOUT TIME ZONE;
    """)
