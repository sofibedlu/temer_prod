# -*- coding: utf-8 -*-
{
    'name': 'Reservation Payment Editor',
    'version': '17.0.1.0.0',
    'category': 'Property Management',
    'summary': 'Edit payment line fields (reference, bank, document type, amount, receipt) from the Reservation Payments view',
    'description': """
        Reservation Payment Editor
        ==========================
        Adds an "Edit Payment" button to the Reservation Payments form and list views.
        Allows authorized users to edit:
          - Reference Number
          - Bank
          - Document Type
          - Amount
          - Transaction Date
          - Payment Receipt (file)

        Changes are saved through the Odoo ORM, so they automatically cascade
        to the Receipt Dashboard (reference number, bank, document type, amount,
        receipt file all update in the linked receipt approval record).
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'ahadubit_property_reservation',
    ],
    'data': [
        'security/reservation_payment_editor_groups.xml',
        'security/ir.model.access.csv',
        'views/payment_edit_wizard_views.xml',
        'views/reservation_payment_views_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
