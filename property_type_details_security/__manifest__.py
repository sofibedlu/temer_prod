{
    'name': 'Property Type Details Security',
    'version': '17.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Secures property type detail fields from being edited by basic sales persons',
    'author': 'Kasahun Ybeltal',
    'depends': ['property_type_details', 'temer_structure', 'temer_property_price_edit', 'temer_property_price_m2_edit', 'property_finishing_rate', 'property_commercial_rate', 'advanced_property_unit_naming', 'commercial_gross_range'],
    'data': [
        'views/property_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
