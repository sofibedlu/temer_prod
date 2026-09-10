{
    'name': 'Property Advance Remaining Tracking',
    'version': '17.0.1.0.0',
    'summary': 'Tracks deferred advance payments across Property Sales and Collection Orders.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base',
        'advanced_property_management',
        'collection_management'
    ],
    'data': [
        'views/property_sale_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}