{
    'name': 'Collection Discount Request Workflow',
    'version': '17.0.1.0.0',
    'summary': 'Adds a request and approval workflow for collection discounts.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'collection_management',
        'property_contract_collection',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/discount_request_views.xml',
        'views/collection_order_views.xml',
        'wizard/discount_request_reject_wizard.xml',
        'wizard/discount_request_wizard_views.xml',
        'wizard/payment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}