{
    'name': 'Collection Request Smart Buttons',
    'version': '17.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Adds collection smart buttons for request workflows.',
    'author': 'Temer',
    'license': 'LGPL-3',
    'depends': [
        'collection_discount_request',
        'collection_payment_extension',
        'property_contract_collection',
        'property_void_request_custom',
        'property_post_sales_refund',
    ],
    'data': [
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
