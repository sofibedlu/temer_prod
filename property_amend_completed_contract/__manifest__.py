{
    'name': 'Property Amend Completed Contract',
    'version': '17.0.1.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'Allows schedule amendment on completed collection orders and updates totals.',
    'depends': [
        'base', 
        'property_contract_extension', 
        'property_contract_collection',
        'collection_management',
        'temer_hotfixes'
    ],
    'data': [
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}