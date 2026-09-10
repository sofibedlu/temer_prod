{
    'name': 'Collection Finance Access',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Extended access rights for Finance users on Collections',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'base',
        'collection_management',
        'payment_approval_new',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}