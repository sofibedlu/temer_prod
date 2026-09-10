# -*- coding: utf-8 -*-
{
    'name': 'Property State Change Control',
    'version': '17.0.1.0.1',
    'category': 'Real Estate',
    'summary': 'Validate Make Draft / Make Available on sold and reserved properties',
    'description': """
        Controls Make Draft and Make Available actions on properties:
        - Blocks sold properties with a clear error message
        - Asks confirmation when changing reserved properties
        - Cancels the active reservation on confirm
        - Logs the action in property chatter with the logged-in user
    """,
    'author': 'Temer Properties',
    'depends': [
        'mail',
        'advanced_property_management',
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'property_audit_log',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/property_state_change_confirm_views.xml',
        'views/property_server_actions.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
