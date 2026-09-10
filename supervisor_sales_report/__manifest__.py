# -*- coding: utf-8 -*-
{
    'name': 'Sales Report',
    'version': '17.0.1.5.0',
    'category': 'Sales',
    'summary': 'Sales Report for Supervisors and Sales Managers',
    'description': """
Sales Report Module
==================
This module provides a comprehensive sales report for supervisors and sales managers:

* Prospect count
* Follow-up activities (site visit, office visit, call, etc.)
* Reservation count
* Sold count from property.reservation (merged uses child.property.salesperson_id)
* Date range filtering
* Role-based data filtering (supervisor/sales manager)
""",
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'temer_structure',
        'temer_crm',
        'ahadubit_property_base',
        'ahadubit_property_reservation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/supervisor_sales_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'supervisor_sales_report/static/src/css/report_styles.css',
            'supervisor_sales_report/static/src/js/supervisor_sales_report_client.js',
            'supervisor_sales_report/static/src/xml/supervisor_sales_report.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
