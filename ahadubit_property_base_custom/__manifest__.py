# -*- coding: utf-8 -*-
{
    'name': "Ahadubit Property Base Custom",
    'version': '17.0.1.0.0',
    'summary': """
        Custom extensions for Ahadubit Property Management
        """,
    'description': """
        Custom extensions for Ahadubit Property Management:
        - Company menu and site company integration
        - City/Subcity domain fixes
    """,

    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",

    'category': 'Sales',

    'depends': [
        'base',
        'mail',
        'ahadubit_property_base',
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Views
        'views/site_company_views.xml',
        'views/property_site_views.xml',
    ],

    'images': [],
    'demo': [],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}

