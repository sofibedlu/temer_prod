{
    'name': 'Property Installment Date Wizard',
    'version': '17.0.1.0.0',
    'summary': 'Wizard to dynamically add shifted date installments with Amharic names.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base', 
        'property_flexible_scheduling', 
        'property_ethiopian_time_schedule'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/add_shifted_installment_wizard_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}