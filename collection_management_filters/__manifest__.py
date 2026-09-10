{
    'name': 'Collection Management Filters',
    'version': "17.0.1.0.0",
    'summary': 'Adds Void and Terminated filters and hides void installments.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['collection_management', 'collection_filter'],
    'data': [
        'views/collection_order_search_views.xml',
        'views/collection_installment_search_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}