{
    'name': 'Collection Outstanding Balance',
    'version': '17.0.1.0.0',
    'summary': 'Dynamic filtering for outstanding progress-based installments.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'collection_management', 
        'collection_progress_integration'
    ],
    'data': [
        'views/outstanding_balance_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}