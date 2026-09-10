{
    'name': 'Collection Payment Multi Extension',
    'version': '17.0.1.0.0',
    'summary': 'Request multiple payment extensions under one reference.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'collection_payment_extension',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/extension_request_views.xml',
        'views/extension_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'collection_payment_multi_extension/static/src/scss/multi_extension.scss',
        ],
    },
    'installable': True,
    'application': False,
}
