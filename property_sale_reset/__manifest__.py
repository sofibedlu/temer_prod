{
    'name': 'Property Sale Reset State',
    'version': '17.0.1.0.0',
    'summary': 'Adds a button to revert Property Sale to Request for Confirm.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'base', 
        'ahadubit_property_base',
        'property_contract_extension',
        'temer_structure',
        'contract_sections',
        'temer_contract_number_site',
    ],
    'data': [
        'security/security.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}