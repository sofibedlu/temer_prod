# -*- coding: utf-8 -*-
{
    'name': 'CRM Custom Menu - Customer Phone Tab',
    'version': '17.0.1.1.3',
    'category': 'Sales',
    'summary': 'Customer Phone tab on Call Center, Website, and Reception forms',
    'description': """
        Country-aware phone normalization for Reception, Website, and Call Center.
        Customer Phone tab on all three channel forms (Country + Phone Number table).
    """,
    'author': 'Temer Properties',
    'depends': ['crm_custom_menu'],
    'data': [
        'views/crm_lead_callcenter_views.xml',
        'views/crm_lead_website_views.xml',
        'views/crm_lead_reception_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
