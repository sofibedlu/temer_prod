# -*- coding: utf-8 -*-
"""
Populate reservation_status on existing receipt.approval.record rows.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE receipt_approval_record rar
        SET reservation_status = pr.status
        FROM property_reservation pr
        WHERE rar.reservation_id = pr.id
          AND rar.reservation_status IS DISTINCT FROM pr.status
    """)
