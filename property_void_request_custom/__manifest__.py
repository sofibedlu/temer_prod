{
    'name': 'Property Void Request Custom Flow',
    'version': '17.0.1.0.0',
    'summary': 'Customizations for the property void and amendment request process.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'account',
        'property_contract_extension',
        'property_contract_collection',
        'temer_structure',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/void_request_views.xml',
        'views/amendment_request_views.xml',
        'views/account_move_views.xml',
        'views/wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}