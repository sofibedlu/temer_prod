{
    'name': 'Property Commission Management',
    'version': '17.0.1.0.0',
    'summary': 'Manage property commissions efficiently',
    'description': """
        Property Commission Management
        ==============================
        This module helps manage commissions related to property sales, rentals, and transactions, 
        keeping track of commission calculations, payment statuses, and commission reports.
    """,
    'category': 'Real Estate',
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'advanced_property_management',  # Example: if you have a custom property management module
    ],
    'data': [
        'security/ir.model.access.csv',  # Define access control rules
        'views/property_commission_views.xml',  # Main view files for the module
        'views/property_commission_menu.xml',  # Menu and navigation items
        'data/commission_data.xml',  # Any necessary demo or initial data
        'report/property_commission_report.xml',  # Report templates and definitions
    ],
    'demo': [
        'demo/property_commission_demo.xml',  # Demo data for testing
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
