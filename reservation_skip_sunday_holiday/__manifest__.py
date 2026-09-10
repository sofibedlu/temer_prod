# -*- coding: utf-8 -*-
{
    'name': 'Reservation Skip Sunday Holiday',
    'version': '17.0.1.0.6',
    'category': 'Property',
    'summary': 'Skip Sundays and public holidays on reservation end dates',
    'description': """
        Skips Sundays and public holidays on reservation expire dates.
        One-time fix on install/upgrade for active reservations (not on
        properties in Pending Sales).
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'ahadubit_property_reservation',
        'special_reservation',
        'custom_property_reservation_extension',
        'custom_property_reservation_convert_regular',
        'special_reservation_final_approve',
        'special_reservation_manager_step',
        'special_reservation_duration_fix',
        'track_time_log_timestamp',
    ],
    'data': [
        'views/special_approval_wizard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
