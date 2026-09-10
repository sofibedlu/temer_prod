{
    'name': 'Batch Due Date Extension',
    'version': '17.0.1.0.0',
    'summary': ':batch due date extensions for collection installments.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['collection_management', 'mail', 'property_sale_buyer_name'],
    'external_dependencies': {'python': ['ethioqen']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/batch_extension_wizard_views.xml',
        'views/batch_extension_request_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}