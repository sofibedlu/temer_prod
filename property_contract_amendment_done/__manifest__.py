{
    'name': 'Property Contract Amendment Done State',
    'version': '17.0.1.0',
    'summary': 'Adds a Done state to Amendment Requests',
    'author': 'Sofonias B/Temerproperties',
    'depends': ['property_contract_collection', 'property_void_request_custom', 'property_contract_extension'],
    'data': [
        'views/amendment_request_views.xml',
    ],
    'installable': True,
    'application': False,
}