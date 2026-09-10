{
    'name': 'CRM Phone Number Validation',
    'version': '17.0.1.0.0',
    'summary': 'Validate phone number uniqueness in CRM leads',
    'category': 'CRM',
    'author': 'Your Name',
    'website': 'https://www.yourcompany.com',
    'depends': ['crm', 'web'],
    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_phone_validation/static/src/js/phone_validation.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}