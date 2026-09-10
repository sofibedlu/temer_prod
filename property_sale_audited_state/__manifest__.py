{
    'name': 'Property Sale Audited State',
    'version': '1.0',
    'summary': 'Adds an Audited state to the property sale lifecycle',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base', 
        'property_contract_extension',
        'temer_structure'
    ],
    'data': [
        'security/security.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}