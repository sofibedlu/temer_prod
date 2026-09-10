{
    'name': 'Collection Management Extension',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Extends collection management tree views and fixes access rights',
    'author': 'Sofonias B/temerproperties',
    'depends': [
        'base',
        'collection_management',
        'property_sale_buyer_name',
        'advanced_property_management',
        'collection_filter',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}