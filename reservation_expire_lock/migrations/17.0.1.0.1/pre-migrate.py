# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE property_reservation
            ADD COLUMN IF NOT EXISTS reservation_lock_on_expire BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS reservation_lock_on_expire_by_id INTEGER,
            ADD COLUMN IF NOT EXISTS reservation_lock_on_expire_date TIMESTAMP WITHOUT TIME ZONE;
    """)

    # Backfill: any active reservation whose property was already scheduled to lock
    # on expiry before this update gets reservation_lock_on_expire = True so the
    # cron still locks it correctly after the upgrade.
    cr.execute("""
        UPDATE property_reservation pr
        SET reservation_lock_on_expire = TRUE
        FROM property_property pp
        WHERE pr.property_id = pp.id
          AND pp.lock_on_expire = TRUE
          AND pr.status IN ('reserved', 'requested');
    """)
