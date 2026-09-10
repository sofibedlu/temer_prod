{
    'name': 'Property Due Date Optional',
    'version': '17.0.1.0.0',
    'summary': 'Allows specific installments to bypass the due date requirement in Time-Based schedules.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base',
        'property_flexible_scheduling',
        'property_partial_due_date_wizard',
        'property_collection_fixes'
    ],
    'data': [
        'views/payment_term_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}