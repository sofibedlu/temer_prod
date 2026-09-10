{
    'name': 'Property Contract Manual Override',
    'version': '1.0',
    'summary': 'Wizard to manually override locked property sale schedules.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['ahadubit_property_base', 'advanced_property_management', 'property_flexible_scheduling'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/contract_override_wizard_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}