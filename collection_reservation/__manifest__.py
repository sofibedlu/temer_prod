{
    'name': 'Collection Reservation',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Create property reservations from collection requests.',
    'author': 'Temer',
    'license': 'LGPL-3',
    'depends': [
        'collection_management',
        'ahadubit_property_reservation',
        'crm_quota_lead_distribution',
        'special_reservation_payment',
    ],
    'data': [
        'security/collection_reservation_security.xml',
        'security/ir.model.access.csv',
        'data/reservation_type_data.xml',
        'data/ir_sequence_data.xml',
        'views/collection_reservation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
