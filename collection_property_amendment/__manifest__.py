{
    'name': 'Collection Property Amendment',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'workflow for amending assigned properties in collection orders.',
    'depends': ['base', 'mail', 'collection_management', 'property_void_request_custom', 'property_contract_extension', 'property_contract_collection'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizards/create_amendment_wizard_views.xml',
        'wizards/confirm_amendment_wizard_views.xml',
        'wizards/reject_amendment_wizard_views.xml',
        'views/property_amendment_request_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
}