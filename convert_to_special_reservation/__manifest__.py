# -*- coding: utf-8 -*-
{
    'name': 'Convert to Special Reservation',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Convert regular/quick reservations to special reservations',
    'description': """
        Convert to Special Reservation Module
        =====================================
        This module adds a "Convert to Special" button to property reservations,
        allowing users to convert regular or quick reservations to special reservations
        that require approval workflow.
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'ahadubit_property_reservation',
        'special_reservation',
    ],
    'data': [
        'views/property_reservation_history_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

