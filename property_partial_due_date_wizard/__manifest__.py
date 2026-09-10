{
    'name': 'Property Partial Due Date Wizard',
    'version': '1.0',
    'author': 'Sofonias B/TemerProperties',
    'license': 'LGPL-3',
    'depends': ['property_flexible_scheduling',
                'ahadubit_property_base',
                'advanced_property_management',
                'property_contract_extension'
            ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/set_due_date_wizard_views.xml',
        'views/property_sale_inherit_views.xml',
    ],
    'installable': True,
    'application': False,
}