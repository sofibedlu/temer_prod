# -*- coding: utf-8 -*-
{
    'name': 'Extension Final Approve',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Adds a final approval step for reservation extensions by a designated final approver (CEO)',
    'depends': [
        'ahadubit_property_reservation',
        'mail',
    ],
    'data': [
        'security/extension_final_approve_groups.xml',
        'security/ir.model.access.csv',
        'views/extension_final_approve_views.xml',
        'views/extension_final_approve_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
