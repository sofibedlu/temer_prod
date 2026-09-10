# -*- coding: utf-8 -*-
{
    'name': 'Temer Payment Request',
    'version': '17.0.1.2.0',
    'category': 'Accounting',
    'summary': 'Payment Request and Payment Order Management',
    'author': 'Temer Properties',
    'depends': ['base', 'account'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/payment_request_sequence.xml',
        'data/payment_order_sequence.xml',
        'wizard/payment_order_cancel_wizard.xml',
        'wizard/account_payment_cancel_wizard.xml',
        'views/payment_request_views.xml',
        'views/payment_order_views.xml',
        'views/account_payment_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'temer_payment_request/static/src/css/payment_states.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}