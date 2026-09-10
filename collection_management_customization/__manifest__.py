{
    'name': 'Collection Management Customization',
    'version': '17.0.1.0.0',
    'summary': 'Customizations for collection management, progress, and Reactivate workflow',
    'author': 'Sofonias B/temerproperties',
    'depends': [
        'collection_management',
        'property_contract_collection',
        'collection_progress_integration',
        'collection_progress_date_override',
        'temer_payment_modify',
    ],
    'data': [
        'security/security.xml',
        'views/collection_order_views.xml',
        'views/progress_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}