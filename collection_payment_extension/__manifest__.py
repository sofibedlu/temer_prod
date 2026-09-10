{
    'name': 'Collection Payment Extension Workflow',
    'version': '17.0.1.0.0',
    'summary': 'Adds an approval workflow for collection payment extensions.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'collection_management',
        'property_contract_collection'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/extension_request_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
}