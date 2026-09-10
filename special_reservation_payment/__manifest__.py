# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Payment',
    'version': '17.0.1.0.9',
    'category': 'Property',
    'summary': 'Payment tab in Special Approval Wizard using transient lines',
    'description': """
        Special Reservation Payment Module
        ===================================
        - Adds payment lines to the Special Approval Wizard using a TransientModel
          so Save never touches the reservation's payment_line_ids
        - If amount > 0: payment section appears; submit blocked until lines match amount
        - On Submit/Approve: temp lines are committed to property.reservation.payment
        - Supervisor/CEO see committed lines read-only with is_verifed toggle
        - On Final Approve: creates receipt_dashboard records for each payment line
        - Fixes pre-existing ensure_one bug in property.reservation.payment.write()
    """,
    'author': 'Temer',
    'depends': [
        'base',
        'mail',
        'special_reservation',
        'special_reservation_final_approve',
        'receipt_dashboard',
        'ahadubit_property_reservation',
        'temer_structure',
        'reservation_payment_ref_edit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/special_approval_wizard_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
