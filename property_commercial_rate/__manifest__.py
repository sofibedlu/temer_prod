# -*- coding: utf-8 -*-
{
    'name': "Property Commercial Rate Range",
    'version': '17.0.1.0.0',
    'summary': "Commercial rate range configuration for properties",
    'author': "Custom",
    'category': 'Sales',
    'depends': [
        'ahadubit_property_base',
        'advanced_property_management',
        'temer_structure',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/commercial_rate_range_views.xml',
        'views/property_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
