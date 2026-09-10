{
    'name': 'Property Ethiopian Time Schedule',
    'version': '1.0',
    'summary': 'Configurable Ethiopian Date translation for installments.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['ahadubit_property_base', 'property_flexible_scheduling', 'property_contract_extension'],
    'external_dependencies': {
        'python': ['ethioqen'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ethiopian_config_data.xml',
        'views/ethiopian_calendar_config_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}