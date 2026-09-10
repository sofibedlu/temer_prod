{
    'name': 'Collection Early Settlement Request Workflow',
    'version': '17.0.1.0.0',
    'summary': 'Adds a request and approval workflow for early settlements.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'collection_management',
        'collection_discount_request',
        'mail',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/early_settlement_request_views.xml',
        'views/collection_order_views.xml',
        'views/early_settlement_wizard_inherit_view.xml',
        'views/settlement_reject_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}