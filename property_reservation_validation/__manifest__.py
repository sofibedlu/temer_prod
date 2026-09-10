# -*- coding: utf-8 -*-
{
    'name': 'Property Reservation Validation',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Validates that one property can only have one active reservation (all types)',
    'description': """
        Property Reservation Validation Module
        =====================================
        This module adds validation to ensure that:
        * One property can only have one active reservation at a time
        * ALL reservation types are validated: Quick, Regular, and Special
        * A property can only be reserved once, regardless of reservation type
        * Prevents duplicate reservations of any type on the same property
    """,
    'author': 'Temer',
    'depends': [
        'base',
        'ahadubit_property_reservation',
    ],
    'data': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

