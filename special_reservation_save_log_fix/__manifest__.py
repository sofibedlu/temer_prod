# -*- coding: utf-8 -*-
{
    'name': 'Special Reservation Save & Log Fix',
    'version': '17.0.1.0.1',
    'category': 'Property',
    'summary': 'Sync Special Approval Save to reservation log; fix Approved→CEO chatter leak',
    'description': """
Special Reservation Save & Log Fix
==================================
1. When Save is clicked on the Special Approval Form, editable fields
   (Duration, Duration unit, Amount, Reason) are always written onto the
   linked reservation (create and write paths) so they persist on reopen
   and appear in the chatter log.

2. Reopens the latest Special Approval wizard for the reservation instead
   of always creating a blank one from defaults.

3. Overrides final-approval re-tracking so the temporary Approved → CEO
   rewind never posts to chatter (there is no UI button for that reverse).
    """,
    'author': 'Temer',
    'depends': [
        'special_reservation',
        'special_reservation_final_approve',
        'special_reservation_duration_fix',
        'special_reservation_payment',
        'reservation_approval_end_date_buffer',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
