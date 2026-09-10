# -*- coding: utf-8 -*-
{
    'name': 'Reservation Type Readonly',
    'version': '17.0.1.0.1',
    'category': 'Property Management',
    'summary': 'Make reservation type read-only on the reservation form',
    'description': """
        Reservation type stays editable while creating a new reservation (e.g. from
        a lead). After the record is saved, the field becomes read-only in draft,
        requested, reserved, and all later states.
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'ahadubit_property_reservation',
        'custom_property_reservation_extension',
        'convert_to_special_reservation',
    ],
    'data': [
        'views/property_reservation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
