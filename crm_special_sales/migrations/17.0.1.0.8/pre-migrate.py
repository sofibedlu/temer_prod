# -*- coding: utf-8 -*-
"""Add access_property_sales_person_group as implied group for group_special_sales
so Special Sales users can read property.salesperson.mapping."""


def migrate(cr, version):
    # Find group_special_sales
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'crm_special_sales' AND name = 'group_special_sales'
    """)
    row = cr.fetchone()
    if not row:
        return
    special_sales_gid = row[0]

    # Find access_property_sales_person_group
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'temer_structure' AND name = 'access_property_sales_person_group'
    """)
    row = cr.fetchone()
    if not row:
        return
    sales_person_gid = row[0]

    # Add implied group if not already set
    cr.execute("""
        INSERT INTO res_groups_implied_rel (gid, hid)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (special_sales_gid, sales_person_gid))
