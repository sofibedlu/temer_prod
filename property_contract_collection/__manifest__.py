{
    'name': 'Property Contract & Collection Adjustments',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temer-Properties',
    'summary': 'Validation on Property Sale payment schedules and contruct amendment and void request-workflow',
    'depends': [
        'base', 
        'ahadubit_property_base', 
        'advanced_property_management',
        'collection_management',
        'property_contract_extension'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/property_sale_views.xml',
        'views/collection_config_views.xml',
        'views/collection_order_views.xml',
        'views/void_request_views.xml',
        'views/amendment_request_views.xml',
        'wizard/amendment_request_approve_wizard_views.xml',
        'wizard/collection_reactivate_wizard_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
}