{
    'name': 'Menu Visibility Manager',
    'version': '17.0.1.0.0',
    'summary': 'Manage menu visibility for user groups',
    'description': """
        This module allows you to:
        - Hide/Show menu items based on user groups
        - Manage menu visibility from a central configuration
        - Apply visibility rules dynamically
    """,
    'category': 'Tools',
    'author': 'Your Name',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_item.xml',
        'views/view.xml',
    ],
    'installable': True,
    'application': True,
}