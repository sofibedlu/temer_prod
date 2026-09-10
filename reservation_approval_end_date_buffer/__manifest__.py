# -*- coding: utf-8 -*-
{
    'name': 'Reservation Approval End Date ',
    'version': '17.0.1.0.8',
    'category': 'Property',
    'summary': 'Approval end-date buffer and tracked manager/CEO approval steps',
    'description': """
        Adds a 5-minute grace period to the reservation expire_date when:
        - A special reservation is manager-approved (before CEO final approval)
        - A reservation extension is sent for final approval (pending → pending final approval)

        Also ensures standard Odoo chatter tracking for:
        - Supervisor Approval → Manager Approval
        - Manager Approval → CEO Approval (+ end date buffer)
        - CEO Approval → Approved (+ duration / end date changes)
    """,
    'author': 'Temer',
    'depends': [
        'special_reservation_manager_step',
        'extension_final_approve',
        'special_reservation_payment',
        'special_reservation_duration_fix',
        'reservation_skip_sunday_holiday',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
