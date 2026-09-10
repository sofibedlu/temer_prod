# -*- coding: utf-8 -*-
{
    'name': 'Collection Reports',
    'version': '17.0.1.0.1',
    'category': 'Collection',
    'summary': 'Collection Reports and Analytics',
    'description': """
        Collection Reports Module
        ========================
        This module provides comprehensive reporting for collection management:
        
        * General Information Report
        * Summarized Report
        * Plan Based on Collection Stage
        * Report Based on Collection Stage
        * Monthly Plan/Report
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'collection_management',
        'advanced_property_management',
    ],
    'data': [
        'security/collection_reports_groups.xml',
        'security/ir.model.access.csv',
        'data/collection_plan_stage_data.xml',
        'data/ir_sequence_data.xml',
        'views/collection_report_views.xml',
        'views/collection_plan_stage_views.xml',
        'views/collection_image_report_views.xml',
        'views/collection_plan_views.xml',
        'views/collection_customer_service_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'collection_reports/static/src/css/report_styles.css',
            'collection_reports/static/src/js/general_info_client.js',
            'collection_reports/static/src/xml/general_info_report.xml',
            'collection_reports/static/src/js/general_info_report.js',
            'collection_reports/static/src/xml/general_info_report_old.xml',
            'collection_reports/static/src/js/summarized_report_client.js',
            'collection_reports/static/src/xml/summarized_report.xml',
            'collection_reports/static/src/js/plan_stage_report_client.js',
            'collection_reports/static/src/xml/plan_stage_report.xml',
            'collection_reports/static/src/js/report_stage_report_client.js',
            'collection_reports/static/src/xml/report_stage_report.xml',
            'collection_reports/static/src/js/collection_stage_report_client.js',
            'collection_reports/static/src/xml/collection_stage_report.xml',
            'collection_reports/static/src/js/actual_paid_report_client.js',
            'collection_reports/static/src/xml/actual_paid_report.xml',
            'collection_reports/static/src/js/communication_report_client.js',
            'collection_reports/static/src/xml/communication_report.xml',
            'collection_reports/static/src/js/customer_service_report_client.js',
            'collection_reports/static/src/xml/customer_service_report.xml',
            'collection_reports/static/src/js/collection_plan_client.js',
            'collection_reports/static/src/xml/collection_plan.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

