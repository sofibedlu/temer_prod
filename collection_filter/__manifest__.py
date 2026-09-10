# -*- coding: utf-8 -*-
{
    'name': 'Collection Filter',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Enhanced search and grouping for Collection Orders',
    'description': """
Collection Filter Module
========================
This module enhances the Collection Orders with advanced search and grouping capabilities:

* Search by customer name
* Search by property name
* Search by site name
* Group by property
* Group by site
* Combined search across customer, property, and site
    """,
    'author': 'Temer Properties',
    'depends': [
        'base',
        'collection_management',
        'ahadubit_property_base',
    ],
    'data': [
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

