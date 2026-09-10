# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Supervisor Filter',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Filter submitted special reservation requests to show only supervisee salespersons',
    'depends': [
        'ahadubit_property_reservation',
        'special_reservation',
        'temer_structure',
    ],
    'data': [
        'security/ir_rule.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
