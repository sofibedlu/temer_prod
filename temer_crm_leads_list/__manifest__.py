{
    'name': 'Temer CRM Leads List',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Tree-only leads view without phone numbers',
    'description': """
        Shows All Leads in a tree-only view (no form, no kanban),
        without the phone number column. No Create button; filter, group by, and export enabled.
    """,
    'author': 'Temer Properties',
    'website': 'https://yourcompany.com',
    'depends': ['temer_crm', 'bus'],
    'data': [
        'security/insite_all_lead_groups.xml',
        'security/ir.model.access.csv',
        'views/leads_list_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'temer_crm_leads_list/static/src/css/insite_lead_list.css',
            'temer_crm_leads_list/static/src/services/groups_reload_service.js',
            'temer_crm_leads_list/static/src/views/list_controller_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
