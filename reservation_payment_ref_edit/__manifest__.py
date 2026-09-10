# -*- coding: utf-8 -*-
{
    'name': 'Reservation Payment Reference Edit Control',
    'version': '17.0.1.0.1',
    'summary': 'Lock Add a Line by role/status. Allow ref_number edit only when receipt is draft.',
    'category': 'Property',
    'author': 'Ahadubit Technologies',
    'license': 'LGPL-3',
    'depends': [
        'ahadubit_property_reservation',
        'temer_structure',
        'receipt_dashboard',
        'temer_reservation_contact_team',
    ],
    'data': [
        'views/reservation_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
