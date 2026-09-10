# -*- coding: utf-8 -*-
{
    'name': "Commercial Gross Range",
    'version': '17.0.1.0.1',
    'summary': "Commercial gross range configuration for properties",
    'author': "Temer Properties",
    'category': 'Sales',
    'depends': [
        'ahadubit_property_base',
        'advanced_property_management',
        'property_commercial_rate',
        'property_type_details',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/commercial_gross_range_views.xml',
        'views/property_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
