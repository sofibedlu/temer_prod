# -*- coding: utf-8 -*-
{
'name': "Custom Report Wizard",
    'version': '17.0.1.0.0',
    'summary': """
        Custom Report Wizard
        """,
    'description': """
        Custom Report Wizard Features:
        - Custom report generation for team activity
    """,

    'author': "Temer Properties",

    'category': 'Reporting',

    'depends': [
        'base',
        'mail',
        'advanced_property_management',
        

        
    ],

    'data': [
                    # Security

        'security/wizard_group.xml',
        'security/ir.model.access.csv',

        #data


        # Views

        'models/team_activity_wizards_views.xml',
        'models/lead_analysis_wizards_views.xml',
        'views/team_activity_reports.xml',
        'views/lead_analysis_reports.xml',
        'views/team_activity_report_menu.xml',
        'views/temer_lead_analysis_wizard_view.xml',
        'views/temer_lead_analysis_report.xml',

            ],
    "assets": {
        "web.assets_backend": [ 
            "custom_report_wizard/static/src/css/**/*",
        ],
    },
 "installable": True,
    "application": True,

}
