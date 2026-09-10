{
    'name': 'Property Schedule Generator Extension',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'Extends property flexible scheduling for due date generation',
    'depends': [
        'property_flexible_scheduling',
        'advanced_property_management',
        'ahadubit_property_base'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/due_date_generator_wizard_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}