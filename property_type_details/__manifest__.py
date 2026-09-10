# -*- coding: utf-8 -*-
{
    'name': 'Property Type Details',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Add property type detail fields directly to property form',
    'description': """
        Property Type Details Module
        ===========================
        This module adds property type detail fields (Number of bedrooms,
        Number of bathrooms, Has maid room, Gross Area, Net Area, Floor Plan)
        directly to the property form as a section, saving them as columns
        in the property table. No code field, no validation constraints.
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'ahadubit_property_base',
        'advanced_property_management',
        'temer_configuration_modify',  # Added to ensure our constraint override runs after its constraint
    ],
    'data': [
        'views/property_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

