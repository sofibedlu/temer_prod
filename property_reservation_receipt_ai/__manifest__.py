{
    'name': 'Property Reservation Receipt AI',
    'version': '1.0',
    'summary': 'Uses AI to extract Reference Number and Amount from deposit slips.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['base', 'ahadubit_property_reservation'], 
    'external_dependencies': {'python': ['requests']},
    'data': [
        'data/ir_config_parameter_data.xml',
        #'views/reservation_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}