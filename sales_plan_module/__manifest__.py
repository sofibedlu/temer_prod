{
    'name': 'Sales Plan',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sales Planning Module',
    'description': """
        Sales Planning and Reporting Module
    """,
    'depends': ['base', 'crm', 'temer_structure'],  # NO wing_structure_list
    'data': [
        'security/ir.model.access.csv',
        'security/sales_plan_security.xml',
        'views/sales_plan_views.xml',  # Main views and menus - only this file should be loaded
        # Note: menu_views.xml, menu_actions.xml, and menu.xml are NOT loaded to avoid conflicts
    ],
    'assets': {
        'web.assets_backend': [
            'sales_plan_module/static/src/js/plan_document_client.js',
            'sales_plan_module/static/src/xml/plan_document_template.xml',
            'sales_plan_module/static/src/css/plan_document_styles.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}