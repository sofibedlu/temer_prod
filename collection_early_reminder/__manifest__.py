{
    'name': 'Collection Early Reminder',
    'version': '17.0.1.0.0',
    'summary': 'Tracks contract-level early payment reminders and request letter counts.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base', 
        'collection_management',
        'letter_template',
        'property_flexible_scheduling'
    ],
    'data': [
        'views/property_sale_views.xml',
        'views/collection_order_views.xml',
        'views/collection_installment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}