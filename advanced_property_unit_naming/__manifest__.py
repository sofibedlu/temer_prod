# __manifest__.py
{
    'name': 'Property Reference Number ',
    'version': '1.0.0',
    'summary': 'Property Reference Number',
    'description': """
        Implements unit naming standard for properties:
        - Format: SiteCode-OwnerCode+ProjectNumber/BlockNumber/FloorNumber-UnitNumber
        - Commercial units add Inside/Outside suffix (I/O)
        - Example: SAR-BLU4/01/F3-01 for residential
        - Example: SAR-BLU4/01/F1-01O for outside commercial unit
    """,
    'category': 'Real Estate',
    'author': 'Selenat',
    'website': 'https://yourwebsite.com',
    'depends': ['advanced_property_management', 'ahadubit_property_base', 'ahadubit_property_base_custom'],
    'data': [
        'views/property_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}