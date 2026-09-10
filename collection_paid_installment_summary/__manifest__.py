{
    'name': 'Collection Paid Installments Summary',
    'version': '1.0',
    'summary': 'dashboard to filter and sum paid installments by site and milestone.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'collection_management',
        'ahadubit_property_base'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/paid_installment_summary_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}