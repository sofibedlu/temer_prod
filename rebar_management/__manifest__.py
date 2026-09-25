{
    'name': 'Rebar Management',
    'version': '1.0.0',
    'category': 'Manufacturing/Construction',
    'summary': 'Manage Rebar Production Requests and Cutting/Bending Specifications',
    'author': 'Sofonias B/Temerproperties',
    'depends': [
        'base',
        'mail',
        'project',
        'product',
        'ahadubit_property_base_custom',  # Provides site.company
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/rebar_site_views.xml',
        'views/rebar_department_views.xml',
        'views/rebar_bar_mark_views.xml',
        'views/rebar_production_request_views.xml',
        'views/rebar_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}