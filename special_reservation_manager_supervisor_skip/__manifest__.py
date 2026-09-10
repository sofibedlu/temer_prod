# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Manager Supervisor Skip',
    'version': '17.0.1.0.4',
    'category': 'Property',
    'summary': 'Skip supervisor approval step for sales and wing managers',
    'description': """
        Sales managers and wing managers have no supervisor in the team structure.
        After a successful special approval submit, the state is set to Supervisor
        Approval so Manager Approve is available. All other submit validation is
        handled by the existing special reservation modules.
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'special_reservation',
        'temer_structure',
        'special_reservation_manager_step',
        'special_reservation_final_approve',
        'special_reservation_payment',
        'special_reservation_duration_fix',
    ],
    'data': [
        'views/special_approval_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
