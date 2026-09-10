# -*- coding: utf-8 -*-
{
    'name': 'Payment Approval Filter',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Enhanced search, filtering, and totals for Payment Approval',
    'description': """
Payment Approval Filter Module
==============================
This module enhances the Payment Approval Dashboard with:

* Search by site name
* Group by site
* Selected total display
* Enhanced search capabilities
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'payment_approval_new',
        'ahadubit_property_base',
    ],
    'data': [
        'views/payment_approval_record_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payment_approval_filter/static/src/js/payment_approval_list.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

