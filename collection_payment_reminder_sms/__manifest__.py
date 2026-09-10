{
    'name': 'Collection Payment Reminder SMS',
    'version': '1.0',
    'summary': 'Automated consecutive SMS payment reminders',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['collection_management', 'temer_contract_number_site', 'ahadubit_property_base_custom'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/sms_cron.xml',
        'views/site_company_views.xml',
        'wizard/sms_reminder_wizard_views.xml',
        'views/sms_template_views.xml',
        'views/sms_log_views.xml',
        
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}