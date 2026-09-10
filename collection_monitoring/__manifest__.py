# -*- coding: utf-8 -*-
{
    'name': 'Collection Monitoring',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Monitor payments sent to Payment Dashboard',
    'description': """
        Collection Monitoring
        ====================
        Adds a Collection Monitoring menu under Collection to view payments
        that go to the Payment Dashboard (payment.approval.record).
        Tree view only with filters and group by: Customer, Property, Site,
        Collection Order.
    """,
    'author': 'Temer Properties',
    'depends': [
        'collection_management',
        'payment_approval_new',
    ],
    'data': [
        'security/collection_monitoring_security.xml',
        'security/ir.model.access.csv',
        'views/collection_monitoring_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'collection_monitoring/static/src/user_groups_reload_service.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
