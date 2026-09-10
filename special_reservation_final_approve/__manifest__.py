# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Final Approve',
    'version': '17.0.1.0.2',
    'category': 'Property',
    'summary': 'Override Final Approve to auto-create reservation type with proper name and payment logic',
    'depends': [
        'ahadubit_property_reservation',
        'special_reservation',
        'temer_structure',
        'mail',
    ],
    'data': [
        'views/special_approval_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
