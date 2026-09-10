{
    'name': 'Property State Workflow Update',
    'version': '17.0.1.0.0',
    'summary': 'Moves the Sold state transition from Confirm to Approve.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base',
        'property_contract_extension',
        # 'advanced_property_management',
        # 'ahadubit_property_reservation',
        # 'ahadubit_crm',
        # 'custom_property_reservation_extension',
        # 'special_reservation'

    ],
    'data': [
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}