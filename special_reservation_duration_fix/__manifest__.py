# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Duration Fix',
    'version': '17.0.1.0.0',
    'summary': 'Persists duration unit (weeks/days/etc.) on special reservation approval wizard',
    'depends': ['special_reservation'],
    'data': [
        'views/reservation_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
