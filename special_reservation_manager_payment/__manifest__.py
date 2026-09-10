# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Manager Payment',
    'version': '17.0.1.0.1',
    'category': 'Property',
    'summary': 'Allow managers to verify and add payment lines in Special Approval Form',
    'description': """
        Special Reservation Manager Payment
        ===================================
        - Grants Call Center Managers (group_manager) access to verify payments
          via the is_verifed toggle in the Special Approval Form
        - Enables "Add a Line" for supervisors and managers during approval steps
          (submitted / supervisor / manager / ceo states)
        - Auto-creates draft receipt.approval.record entries when a new payment
          line is added during the approval workflow
    """,
    'author': 'Temer',
    'depends': [
        'special_reservation_payment',
        'special_reservation_manager_step',
        'temer_structure',
    ],
    'data': [
        'views/special_approval_wizard_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
