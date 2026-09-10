# -*- coding: utf-8 -*-
{
    'name': "Reservation Expire Lock",
    'version': '17.0.1.0.1',
    'summary': "Lock property when reservation expires",
    'description': "When a reserved property's reservation expires (not sold), put the property in lock state instead of available. Locked properties are excluded from reservations; only privileged users can unlock.",
    'category': 'Sales',
    'author': 'Ahadubit Technologies',
    'website': 'https://ahadubit.com',
    'license': 'LGPL-3',
    'depends': [
        'ahadubit_property_reservation',
        'property_lock_unlock',
    ],
    'data': [
        'data/ir_cron_expired_reservation_lock.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
