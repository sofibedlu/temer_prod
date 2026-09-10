{
    'name': 'Collection Segmentation Reporting',
    'version': '1.0',
    'summary': 'Advanced segmented reporting for collection installments.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'collection_management', 
        'ahadubit_property_base',
        'property_contract_collection',
        'property_advance_remaining'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/segmentation_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}