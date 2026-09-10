# -*- coding: utf-8 -*-
{
    'name': 'Property Change Log & Bank Search',
    'version': '17.0.1.0.5',
    'category': 'Real Estate',
    'summary': 'Log every property change in chatter; searchable bank on payments',
    'description': """
        Every user who edits a property gets a line in the property chatter
        (old value → new value). No extra roles or menus.
        Bank field on reservation payments is searchable by name and account number.
    """,
    'author': 'Temer Properties',
    'depends': [
        'mail',
        'advanced_property_management',
        'ahadubit_property_base',
        'property_lock_unlock',
        'ahadubit_property_reservation',
        'bank_configuration_update',
    ],
    'data': [
        'views/bank_configuration_views.xml',
        'views/reservation_payment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
