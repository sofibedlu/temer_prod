{
    'name': 'Collection Settlement Discount Request',
    'version': '17.0.1.0.0',
    'summary': 'Integrates discount requests into the partial settlement workflow',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'collection_partial_settlement', 
        'collection_discount_request'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partial_settlement_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}