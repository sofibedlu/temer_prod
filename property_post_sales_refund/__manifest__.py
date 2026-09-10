{
    'name': 'Property Post Sales Refund',
    'version': '17.0.1.0.0',
    'summary': 'Handles post-sales refund requests for voided property contracts.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'account',
        'mail',
        'property_contract_extension',
        'property_contract_collection',   
        'advanced_property_management',
        'collection_management',
        'property_sale_buyer_name',
        'property_void_request_custom'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/void_request_views_ext.xml',
        'views/post_sales_refund_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}