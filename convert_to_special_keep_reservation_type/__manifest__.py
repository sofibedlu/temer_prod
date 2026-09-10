# -*- coding: utf-8 -*-
{
    'name': 'Convert to Special Keep Reservation Type',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Keep reservation type when converting to special',
    'description': """
        Keep Reservation Type on Convert to Special
        ===========================================
        Overrides the Convert to Special action so regular reservations remain
        regular and quick reservations remain quick after conversion.
    """,
    'author': 'Selenat Alamerew',
    'depends': [
        'convert_to_special_reservation',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
