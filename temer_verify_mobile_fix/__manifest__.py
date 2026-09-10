{
    'name': 'Temer Verify Mobile Fix',
    'version': '17.0.1.0.0',
    'summary': 'Shows is_verifed toggle in kanban (mobile) view for payment lines',
    'depends': [
        'temer_structure',
        'ahadubit_property_reservation',
    ],
    'data': [
        'views/reservation_payment_kanban_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
