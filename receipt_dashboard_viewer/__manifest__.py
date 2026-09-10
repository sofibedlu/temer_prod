# -*- coding: utf-8 -*-
{
    'name': 'Receipt Dashboard Viewer & Site Company',
    'version': '17.0.1.0.7',
    'category': 'Accounting',
    'summary': 'View-only role and Site Company column for Receipt Dashboard',
    'description': """
        Adds to Receipt Dashboard (without modifying the base module):
        * Receipt Dashboard Viewer role — browse only, no check/approve/deny
        * Site Company column on the list and form
        * Filter and group by Site Company
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'receipt_dashboard',
        'ahadubit_property_base',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/receipt_approval_record_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
