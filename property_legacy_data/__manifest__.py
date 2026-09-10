{
    'name': 'Property Legacy Data Entry',
    'version': '1.0',
    'author': 'Sofonias B/TemerProperties',
    'summary': 'Allow manual entry of legacy property sales and contracts',
    'depends': [
        'base', 
        'advanced_property_management', 
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'contract_sections'
    ],
    'data': [
        'security/legacy_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/property_legacy_sale_views.xml',
    ],
    'installable': True,
    'application': False,
}