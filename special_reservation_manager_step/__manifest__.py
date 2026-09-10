# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Manager Approval Step',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Adds a manager approval step between supervisor approve and final (CEO) approve in Special Sales',
    'description': """
        Special Reservation Manager Approval Step
        ==========================================
        Inserts a Manager Approval step into the Special Reservation approval workflow:

        Before: Submitted → Supervisor Approve → CEO Final Approve
        After:  Submitted → Supervisor Approve → Manager Approve → CEO Final Approve

        - "Supervisor Approve" button: visible to users in the Supervisor group (state = submitted)
          → moves state to 'supervisor'
        - "Manager Approve" button: visible ONLY to users with the Manager role in the
          Call Center group (state = supervisor)
          → moves state to 'ceo'
        - "Final Approve" button: visible to CEO group (state = ceo) — unchanged
        - Notifications: manager group users are notified when supervisor approves
    """,
    'author': 'Temer',
    'depends': [
        'special_reservation',
        'special_reservation_final_approve',
        'custom_property_reservation_extension',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/special_approval_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
