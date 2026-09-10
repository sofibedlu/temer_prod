# -*- coding: utf-8 -*-
{
    'name': "Ahadubit CRM",
    'version': '17.0.1.0.0',
    'summary': """
        CRM management system with advanced features
        """,
    'description': """
        CRM
    """,

    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",

    'category': 'crm',

    'depends': [
        'base',
        'mail',
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'crm','sale_crm'
    ],

    'data': [
        #Security
        'security/crm_access_group.xml',
        'security/ir.model.access.csv',
        # Views
        'views/crm_lead_inherited_view.xml',
        'views/base_activity_inherited_view.xml',
        'views/my_activities.xml',

        #data
        'data/crm_activity_data.xml',
        'data/crm_stage_data.xml',
        'data/expire_lead_cron.xml',

        #report
        'report/crm_lead_log_report.xml'

    ],
    'assets': {
        'web.assets_backend': [
            'ahadubit_crm/static/src/css/style.css',
        ],
    },
  
    'images': ['static/description/icon.png'],

    'demo': [
       
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}