# -*- coding: utf-8 -*-
{
    'name': 'Team Activity Report',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Detailed Team Activity Report with PDF and Excel Export',
    'description': """
Team Activity Report
====================
This module provides a detailed team activity report showing:

* Wing, Wing Manager, Supervisor, and Salesperson hierarchy
* Activity counts: Office Visit, Site Visit, Call, EmailSMS
* Total Events calculation
* Date range filtering
* PDF and Excel export functionality
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'supervisor_sales_report',
        'temer_structure',
        'temer_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/team_activity_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'team_activity_report/static/src/css/team_activity_report_styles.css',
            'team_activity_report/static/src/js/team_activity_report_client.js',
            'team_activity_report/static/src/xml/team_activity_report.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

