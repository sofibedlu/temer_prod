{
    'name': 'Property Flexible Scheduling',
    'version': '1.0',
    'author': 'Sofonias B/TemerProperties',
    'summary': 'Generates flexible payment schedules',
    'depends': [
        "advanced_property_management",
        "ahadubit_property_base",
        "ahadubit_property_reservation",
        "temer_payment_modify",
        "temer_hotfixes",
        "property_legacy_data",
        "collection_management",
        "property_contract_extension",
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/legacy_sale_views.xml',
        'views/property_sale_extension_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}