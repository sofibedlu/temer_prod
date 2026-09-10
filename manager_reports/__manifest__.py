# -*- coding: utf-8 -*-
{
    'name': 'Manager Reports',
    'version': '17.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Comprehensive Manager Reports for Stock, Sales, and Collection',
    'description': """
        Manager Reports Module
        =====================
        This module provides comprehensive reporting for managers:
        
        * Stock/Inventory Report - Sites handed over, available, contracts, reservations
        * Sales Performance Report - Daily sales metrics with plans and achievements
        * Collection Report - Collection performance and metrics
        * Stock and Collection Summary - Combined stock and collection overview
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'web',
        'ahadubit_property_base',
        'collection_management',
        'advanced_property_management',
        'temer_crm',
    ],
    'data': [
        'security/manager_reports_groups.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/manager_reports_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'manager_reports/static/src/css/manager_reports.css',
            'manager_reports/static/src/js/stock_inventory_report_client.js',
            'manager_reports/static/src/xml/stock_inventory_report.xml',
            'manager_reports/static/src/js/sales_performance_report_client.js',
            'manager_reports/static/src/xml/sales_performance_report.xml',
            'manager_reports/static/src/js/weekly_sales_by_wing_report_client.js',
            'manager_reports/static/src/xml/weekly_sales_by_wing_report.xml',
            'manager_reports/static/src/js/weekly_report_client.js',
            'manager_reports/static/src/xml/weekly_report.xml',
            'manager_reports/static/src/js/collection_report_client.js',
            'manager_reports/static/src/xml/collection_report.xml',
            'manager_reports/static/src/js/stock_collection_summary_client.js',
            'manager_reports/static/src/xml/stock_collection_summary.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

