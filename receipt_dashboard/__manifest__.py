# -*- coding: utf-8 -*-
{
    'name': 'Receipt Dashboard',
    'version': '17.0.1.0.9',
    'category': 'Accounting',
    'summary': 'Receipt Approval Dashboard for Property Reservations',
    'description': """
        Receipt Dashboard Module
        ========================
        This module provides a dashboard for approving reservation payment receipts:
        
        * Receives payment lines from reservations when status changes to "pending approval"
        * Dashboard with receipt records showing customer, site, property, amount, reference, receipt file
        * Approve action creates receipt (account.move) and reserves the property
        * Deny action with reason type selection and description
        * Full mail tracking and activity logging
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'mail',
        'account',
        'advanced_property_management',
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'ps_binary_field_attachment_preview',
    ],
    'data': [
        'security/receipt_dashboard_groups.xml',
        'security/ir.model.access.csv',
        'security/receipt_dashboard_record_rules.xml',
        'data/receipt_denial_reason_type_data.xml',
        'views/receipt_denial_reason_type_views.xml',
        'views/receipt_denial_reason_views.xml',
        'wizard/receipt_deny_wizard_views.xml',
        'views/receipt_approval_record_views.xml',
        'views/receipt_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'receipt_dashboard/static/src/js/receipt_approval_list.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

