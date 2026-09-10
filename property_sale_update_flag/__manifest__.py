{
    'name': 'Property Sale Update Flag',
    'version': '17.0.1.0.0',
    'summary': 'Flags property sales when updated to filter them for approval.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'base',
        'ahadubit_property_base',
        'property_contract_extension',
        'contract_sections',
    ],
    'data': [
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}