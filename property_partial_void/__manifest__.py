{
    'name': 'Property Partial Void',
    'version': '17.0.1.0.0',
    'summary': 'Workflow to partially drop units from a merged property contract.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'collection_management', 
        'property_merge_management', 
        'mail',
        'property_contract_collection',
        'property_contract_extension',
        'property_void_request_custom'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partial_void_wizard_views.xml',
        'wizard/partial_void_reject_wizard_views.xml',
        'views/partial_void_request_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}