{
    'name': 'Collection Data Reconciliation',
    'version': '1.0',
    'summary': 'Record-specific wizard to reconcile Sale and Collection Installment mismatches.',
    'author': 'Sofonias B/TemerProperties',
    'depends': ['collection_management', 'property_flexible_scheduling'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/reconciliation_wizard_views.xml',
        'views/collection_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}