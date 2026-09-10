{
    'name': 'Property Organizational Unit Workflow',
    'version': '1.0',
    'summary': 'Branch-based approval assignments and restrictions for Property Sales.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['ahadubit_property_base', 'advanced_property_management'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/org_unit_views.xml',
        'views/org_assignment_views.xml',
        'views/property_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}