{
    'name': 'Property Sale Check State',
    'version': '17.0.1.0.0',
    'summary': 'Adds an Audit state in Property Sale',
    'author': 'Sofonias B/Temerproperties',
    'depends': ['ahadubit_property_base', 'property_contract_extension', 'temer_structure', 'advanced_property_management'],
    'data': [
        'security/security.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}