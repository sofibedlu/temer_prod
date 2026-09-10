# -*- coding: utf-8 -*-
{
    'name': "Ahadubit Property Management",
    'version': '17.0.1.0.0',
    'summary': """
        Property Management System
        """,
    'description': """
        Property Management System Features:
    """,

    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",

    'category': 'Sales',

    'depends': [
        'base',
        'mail',
        'advanced_property_management'
    ],

    'data': [
        # Security
        'security/property_access_group.xml',
        'security/ir.model.access.csv',

        #data
        'data/property_floor_data.xml',

        # Views
        'views/property_sale_views.xml',
        'views/property_views.xml',
        'views/config_views.xml',
        'views/crm_views.xml',
        'views/property_reservation_config_views.xml',
        'wizard/cancellation_reason_wizard_views.xml',
        'wizard/property_sale_report_w.xml',
        'reports/property_sale_report.xml'
    ],
    "assets": {
        "web.assets_backend": [
            "ahadubit_property_base/static/src/css/**/*",
        ],
    },

    'images': ['static/description/icon.ico'],
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}