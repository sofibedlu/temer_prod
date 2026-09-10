# -*- coding: utf-8 -*-
{
    'name': "Reservation Assigned Sales",
    'version': '17.0.1.0.0',
    'summary': "Let assigned contract admins finalize reservations into sales.",
    'description': """
        - Provide an 'Assigned Sales' menu for contract admins.
        - Show reservations assigned to the logged-in user.
        - Allow the assigned user to click 'Sold' and continue the normal sale flow.
    """,
    'author': "Temer",
    'category': 'Property',
    'depends': [
        'advanced_property_management',
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'temer_reservation_contact_team',
        'contract_sections',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/reassign_wizard_views.xml',
        'views/reservation_assigned_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

