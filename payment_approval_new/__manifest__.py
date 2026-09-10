# -*- coding: utf-8 -*-
{
    'name': 'Payment Dashboard',
    'version': '17.0.1.0.4',
    'category': 'Accounting',
    'summary': 'Fresh Payment Approval System for Collection Payments',
    'description': """
        Payment Approval System Module (Fresh Implementation)
        =====================================================
        This module provides a fresh dashboard for approving collection payments:
        
        * Stores payment records before invoice creation
        * Dashboard with Incoming and Outgoing payment tabs
        * Approve/Deny actions for payment records
        * Date range filtering
        * Tree view with selection for bulk operations
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'mail',
        'account',
        'collection_management',
        'ps_binary_field_attachment_preview',
    ],
    'data': [
        'security/payment_approval_groups.xml',
        'security/payment_approval_record_rules.xml',
        'security/ir.model.access.csv',
        'wizard/payment_deny_handler_views.xml',
        'wizard/payment_wizard_handler_views.xml',
        'views/payment_approval_record_views.xml',
        'views/collection_installment_views.xml',
    ],
    'post_init_hook': 'post_init_recompute_pending_installments',
    'post_migrate_hook': 'post_migrate_patch_pay_button',
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

