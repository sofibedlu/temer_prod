{
    'name': 'Ethiopian Date Converter',
    'version': '17.0.1.0.0',
    'summary': 'Utility for Ethiopian dates',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'base', 
        'property_post_sales_refund',
        'collection_payment_multi_extension'
    ],
    'external_dependencies': {
        'python': ['ethiopian_date'],
    },
    'data': [
        'views/post_sales_refund_views_ext.xml',
        'views/multi_extension_views_ext.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}