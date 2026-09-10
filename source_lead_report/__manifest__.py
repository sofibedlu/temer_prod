# -*- coding: utf-8 -*-
{
    'name': 'Source Lead Report',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Lead Report filtered by Source (6033 and Walking)',
    'description': """
Source Lead Report
==================
This module provides a lead report filtered by source:

* Filter by source: 6033 and Walking only
* Date range filtering (from/to)
* Display leads in a table format
* PDF and Excel export functionality
* Shows all leads (not user-based filtering)
    """,
    'author': 'TEMER',
    'depends': [
        'base',
        'temer_crm',
        'utm',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/source_lead_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'source_lead_report/static/src/css/source_lead_report_styles.css',
            'source_lead_report/static/src/js/source_lead_report_client.js',
            'source_lead_report/static/src/xml/source_lead_report.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

