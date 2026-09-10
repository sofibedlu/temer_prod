{
    'name': 'CRM Lead Creation Restriction',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'Restrict CRM lead creation to specific group',
    'description': """
        This module restricts the creation of CRM leads to only users belonging to a specific group.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['crm'],
    'data': [
        'data/groups_data.xml',
        'security/crm_lead_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}









