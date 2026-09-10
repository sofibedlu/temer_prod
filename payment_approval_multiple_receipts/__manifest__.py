{
    'name': 'Multiple Receipts for Pending Payments',
    'version': '17.0.1.0.0',
    'summary': 'Allow registering multiple payment receipts for a single pending installment.',
    'author': 'Sofonias B/Temerproperties',
    'depends': ['payment_approval_new', 'collection_management', 'property_contract_extension'],
    'data': [
        'views/collection_installment_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}