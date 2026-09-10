{
    'name': 'Property Contract Discount Extension',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'Apply custom discounts to specific installments on confirmed property sales.',
    'depends': [
        'base',
        'ahadubit_property_base',
        'property_contract_collection',
        'property_flexible_scheduling',
        'collection_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/apply_discount_wizard_views.xml',
        'views/property_sale_views.xml',
        'views/property_payment_line_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}