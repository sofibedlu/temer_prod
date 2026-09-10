# -*- coding: utf-8 -*-
{
    'name': 'Property Reference Floor ID',
    'version': '17.0.1.0.8',
    'summary': 'Property reference uses stored floor_id',
    'description': """
        Uses floor_id for computed_reference (not non-stored floor_ids).
        On install/upgrade fixes auto-generated refs missing the floor segment.
        Skips non-bulk properties that already have a property sale with installments.
        User-edited references are not changed.
        Uninstall "Property Reference Floor Fix" before installing this module.
        Property list → Action → Fix Missing Floor References.
    """,
    'category': 'Real Estate',
    'author': 'Selenat',
    'depends': [
        'advanced_property_unit_naming',
        'ahadubit_property_base',
        'bulk_property_registration',
        'property_name_update_button',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'data': [
        'data/fix_references_action.xml',
    ],
}
