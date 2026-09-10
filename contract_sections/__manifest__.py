# -*- coding: utf-8 -*-
{
    'name': 'Contract Sections',
    'version': '17.0.1.0.0',  # Updated to match your Odoo version
    'category': 'Sales/Contracts',
    'summary': 'Manage contract sections',
    'description': """
        This module allows you to manage contract sections.
        You can create, edit, and organize different sections of contracts.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail','advanced_property_management',
        'advanced_property_management','ahadubit_property_reservation'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_template_views.xml',
        'views/contract_form_view.xml',
        'reports/property_report.xml',
        'reports/reservation_report.xml',
        'views/property_sale.xml',
        'data/sequence.xml',
        'data/contract_template_content_data.xml',
        'views/site_developer.xml',
        'reports/custom_internal_layout.xml',
        'reports/contract_report.xml',
    ],
    'external_dependencies': {
        'python': ['ethiopian_date'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'contract_sections/static/src/css/contract_style.css',
        ],
    },
}