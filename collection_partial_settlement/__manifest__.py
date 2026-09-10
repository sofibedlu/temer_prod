{
    'name': 'Collection Partial Settlement',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'Merge selected installments',
    'depends': ['collection_management', 'collection_discount_request'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partial_settlement_wizard_views.xml',
        'views/collection_order_views.xml',
        'views/collection_installment_views.xml',
    ],
    'installable': True,
    'application': False,
}