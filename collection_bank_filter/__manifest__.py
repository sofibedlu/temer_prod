{
    'name': 'Collection Payment Bank Filter',
    'version': '1.0',
    'summary': 'Filters available banks in the payment wizard based on user assigned sites.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['collection_management', 'ahadubit_property_reservation', 'bank_configuration_update', 'payment_approval_new', 'temer_contract_number_site'],
    'data': [
        'views/payment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}