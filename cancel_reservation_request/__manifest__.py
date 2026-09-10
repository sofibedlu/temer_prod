{
    'name': 'Cancel Reservation Request',
    'version': '17.0.1.0.0',
    'summary': 'Approval workflow for regular and special reservation cancellation',
    'category': 'Property Management',
    'author': 'Temer',
    'license': 'LGPL-3',
    'depends': [
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'property_reservation_cancel_extend',
        'temer_structure',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/cancel_reservation_request_views.xml',
        'wizard/cancel_reservation_request_wizard_views.xml',
        'views/property_reservation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
