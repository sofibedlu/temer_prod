{
    'name': 'crm_additional_feature',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'Adds custom save button to CRM lead form',
    'description': """
        This module adds a custom save button to the CRM lead form that calls the action_save_crm_records method.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['crm'],
    'data': [
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}