{
    'name': 'Property Support Management',
    'version': '1.1',
    'summary': 'Manage Job Orders for Site Operations',
    'sequence': 10,
    'description': """
Support Management / Job Order Module
======================================
This module provides job orders support for property sites, allowing managers to assign tasks and users to report their work.
    """,
    'category': 'Real Estate/Property',
    'author': 'Girma M.',
    'depends': ['base', 'ahadubit_property_base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/support_management_views.xml',
        'views/support_team_views.xml',
        'views/support_category_views.xml',
        'views/support_department_views.xml',
        'views/support_history_views.xml',
        'views/support_config_views.xml',
        'wizard/support_report_wizard_views.xml',
        'wizard/support_weekly_report_views.xml',
        'wizard/additional_task_wizard_views.xml',
        'report/support_weekly_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
