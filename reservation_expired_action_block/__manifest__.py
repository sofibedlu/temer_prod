# -*- coding: utf-8 -*-
{
    'name': 'Reservation Expired Action Block',
    'version': '17.0.1.0.4',
    'category': 'Property',
    'summary': 'Block convert and approval actions on expired or canceled reservations',
    'description': """
        Blocks conversion and approval actions when a reservation is expired or
        canceled, including:
        - Convert to special / convert to regular
        - Special reservation approval (submit, supervisor, manager, final)
        - Reservation extension request, approval (first and final step)
        - Confirm Sales (when reservation contract team module is installed)
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'ahadubit_property_reservation',
        'special_reservation',
        'convert_to_special_reservation',
        'custom_property_reservation_extension',
        'extension_final_approve',
        'temer_reservation_contact_team',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
