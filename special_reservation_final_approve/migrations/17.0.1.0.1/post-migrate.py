# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Set notification_type = 'inbox' for all users who need mobile push notifications:
    - All users in special_reservation.group_ceo
    - All users in special_reservation.group_supervisor
    - All users in special_reservation.group_manager
    - All users in temer_structure.access_property_sales_supervisor_group
    This ensures Odoo sends VAPID web push to their registered devices.
    """
    cr.execute("""
        UPDATE res_users
        SET notification_type = 'inbox'
        WHERE active = true
          AND id IN (
            -- CEO group
            SELECT uid FROM res_groups_users_rel
            WHERE gid IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'special_reservation'
                  AND name IN ('group_ceo', 'group_supervisor', 'group_manager')
            )
            UNION
            -- Sales supervisor group
            SELECT uid FROM res_groups_users_rel
            WHERE gid IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'temer_structure'
                  AND name = 'access_property_sales_supervisor_group'
            )
          )
    """)
    updated = cr.rowcount
    _logger.info('post-migrate: set notification_type=inbox for %d users', updated)
