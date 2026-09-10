{
    'name': 'Installment Update',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Update installment schedules for property sales',
    'author': 'Kasahun Ybeltal',
    'depends': [
        'collection_management',
        'property_legacy_data',
        'advanced_property_management',
        
        'property_flexible_scheduling',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/installment_update_views.xml',
        'views/installment_update_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
