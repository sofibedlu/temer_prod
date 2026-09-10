{
    'name': 'Installment Bulk Letter',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Select a site, filter installments by name, pick a letter type and generate DOCX letters in bulk',
    'author': 'Temerproperties',
    'depends': [
        'collection_management',
        'letter_template',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/installment_bulk_letter_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
