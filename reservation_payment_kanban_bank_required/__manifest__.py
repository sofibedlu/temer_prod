# -*- coding: utf-8 -*-
{
    'name': 'Reservation Payment Kanban Bank Required',
    'version': '17.0.1.0.0',
    'category': 'Property Management',
    'summary': 'Require Bank on mobile Kanban payment create/edit forms',
    'description': """
        Mobile uses the Kanban view for reservation payment lines. The Kanban flow
        opens a payment form without a required Bank field, so lines could be saved
        with an empty bank_id while the desktop tree blocks it.

        This module adds required Bank validation only on:
        - the mobile payment popup form
        - the inline form used by the payment Kanban Add action
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'ahadubit_property_reservation',
        'temer_structure',
    ],
    'data': [
        'views/reservation_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
