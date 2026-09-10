# -*- coding: utf-8 -*-
"""
Fix ir.attachment access for special_attachment_ids.

Existing attachments linked via the Many2many relation table may not have
res_model/res_id set to the reservation, causing Access Error for non-admin
users when opening the reservation form. This migration patches them.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Set res_model/res_id on all special reservation attachments."""
    cr.execute("""
        UPDATE ir_attachment ia
        SET res_model = 'property.reservation',
            res_id    = rel.reservation_id
        FROM property_reservation_special_attachment_rel rel
        WHERE rel.attachment_id = ia.id
          AND (ia.res_model IS DISTINCT FROM 'property.reservation'
               OR ia.res_id IS DISTINCT FROM rel.reservation_id)
    """)
    _logger.info(
        "special_reservation_final_approve migration 17.0.1.0.2: "
        "fixed %d ir.attachment records", cr.rowcount
    )
