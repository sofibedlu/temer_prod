{
    'name': 'Modify Property',
    'category': 'Sales',
    'author': 'Temer Realestate',
    'website': 'https://temerproperties.com/',
    'depends': ['ahadubit_property_reservation','ahadubit_property_base','crm','mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/property_site_view.xml',
        'views/property_site_construction.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
}
