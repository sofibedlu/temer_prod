# -*- coding: utf-8 -*-
{
    'name': "Property Lock / Unlock",
    'version': '17.0.1.0.2',
    'summary': "Lock and unlock properties with role-based privileges",
    'description': """
        Lock properties (draft/available only) for users with Lock privilege.
        Unlock for users with Unlock privilege.
        Locked properties: gray row, lock icon, excluded from reservations.
    """,
    'category': 'Sales',
    'author': 'Ahadubit Technologies',
    'website': 'https://ahadubit.com',
    'license': 'LGPL-3',
    'depends': [
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'temer_crm',
    ],
    'data': [
        'security/property_lock_groups.xml',
        'security/ir.model.access.csv',
        'views/property_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'property_lock_unlock/static/src/css/property_lock.css',
            'property_lock_unlock/static/src/js/list_controller_patch.js',
            'property_lock_unlock/static/src/js/form_controller_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
