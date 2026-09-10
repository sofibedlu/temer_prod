{
    'name': 'MY Team',
    'version': '17.0.1.0.0',
    'summary': 'View your team hierarchy based on your role (Wing Manager / Sales Manager)',
    'description': """
        MY Team
        =======
        Allows Wing Managers and Sales Managers to view their full team hierarchy:
        - Wing Manager sees all teams, supervisors, and salespersons under their wing.
        - Sales Manager sees all supervisors and salespersons under their team.
    """,
    'category': 'Sales',
    'author': 'Temer Properties',
    'website': 'https://www.temerproperties.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'temer_structure',
    ],
    'data': [
        'security/access_group.xml',
        'security/ir.model.access.csv',
        'views/my_team_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
