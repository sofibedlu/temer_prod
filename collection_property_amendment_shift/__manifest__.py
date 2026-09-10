{
    'name': 'Collection Property Amendment - Site Shift',
    'version': '1.0',
    'author': 'Sofonias B/TemerProperties',
    'summary': 'Extends the property amendment workflow to support transferring customers to new sites.',
    'depends': [
        'collection_property_amendment', 
        'ahadubit_property_base'
    ],
    'data': [
        'views/collection_order_views.xml',
        'views/property_sale_views.xml',
        'views/property_amendment_request_views.xml',
        'wizards/create_amendment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}