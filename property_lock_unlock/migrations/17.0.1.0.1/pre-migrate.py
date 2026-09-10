# -*- coding: utf-8 -*-
def migrate(cr, version):
    cr.execute("""
        ALTER TABLE property_property
            ADD COLUMN IF NOT EXISTS lock_on_expire BOOLEAN DEFAULT FALSE;
    """)
