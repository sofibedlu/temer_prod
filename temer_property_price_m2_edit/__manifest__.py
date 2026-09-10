# -*- coding: utf-8 -*-
{
    'name': "Property Price(m2) Edit",
    'version': '17.0.1.0.0',
    'summary': "Allow manual editing of Price(m2) and keep Sales Price calculated.",
    'description': """
        - Make Price(m2) editable on the property form (in draft).
        - When user edits Price(m2), Sales Price (and Rent/Month) are recalculated automatically.
        - Optional: keep manually entered Price(m2) even if floor/site configuration changes.
    """,
    'author': "Temer",
    'category': 'Property',
    'depends': [
        'ahadubit_property_base',
        'ahadubit_floor_price_range',
        'temer_property_price_edit',
    ],
    'data': [
        'views/property_property_price_m2_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

