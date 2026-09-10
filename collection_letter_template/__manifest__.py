{
    'name': 'Collection Letter Dynamic Templates',
    'version': '17.0.1.0.0',
    'summary': 'Configurable payment letters for Collection Management',
    'author': 'Sofonias B/Temerproperties',
    'depends': ['collection_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/collection_letter_template_views.xml',
        'views/print_letter_wizard_views.xml',
        'reports/dynamic_letter_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}