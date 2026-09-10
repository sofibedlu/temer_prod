{
    'name': 'Property Standard Payment Terms',
    'version': '17.0.1.0.0',
    'summary': 'Filters payment lines by a standard boolean flag when creating property sales.',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'ahadubit_property_base',
        'temer_payment_modify',
    ],
    'data': [
        'views/payment_term_views.xml',
    ],
    'installable': True,
    'application': False,
}