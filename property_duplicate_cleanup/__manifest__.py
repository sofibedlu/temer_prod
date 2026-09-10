{
    'name': 'Property Duplicate Cleanup',
    'version': '1.0',
    'summary': 'transfer related records from duplicated invalid properties to valid ones.',
    'author': 'Sofonias B/TemerProperties',
    'depends': [
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'collection_management'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/property_property_views.xml',
        'wizard/duplicate_cleanup_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}