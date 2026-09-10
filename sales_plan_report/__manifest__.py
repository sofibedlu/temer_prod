{
    'name': 'Sales Plan Report',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sales Plan Reporting',
    'description': 'Generate Wing and Supervisor Reports with actual data from database',
    'depends': ['base', 'sales_plan_module'],
    'data': [
        'security/ir.model.access.csv',  # This should exist
        'views/sales_report_views.xml',
        'views/sales_report_menus.xml',
        'reports/sales_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sales_plan_report/static/src/css/sales_report.css',
            'sales_plan_report/static/src/js/sales_report_client.js',
            'sales_plan_report/static/src/xml/sales_report.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}