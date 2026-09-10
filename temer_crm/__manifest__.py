{
    'name': 'Temer Customer Management',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Lead management with optimized phone validation',
    'description': """
        Custom lead management system with database-level phone validation
        for high concurrency environments (300+ users).
    """,
    'author': 'Temer Properties',
    'website': 'https://yourcompany.com',
    'depends': ['base', 'mail','ahadubit_property_base','crm','contacts',],
    'data': [
        'security/temer_lead_security.xml',
        'security/ir.model.access.csv',
        'views/temer_lead_views.xml',
        'views/temer_phone_views.xml',
        'data/lead_scheduler.xml',
        'reports/temer_lead_report_actions.xml',
        'reports/temer_lead_report.xml',
        'views/stage_history_views.xml',
        'views/activities_analysis_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}