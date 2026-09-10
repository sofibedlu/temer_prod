{
    'name': 'Temer CRM – Amharic PDF Reports',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Fix Amharic and other Ethiopic script in Lead Activity Report PDF',
    'description': """
        Ensures Amharic (and other Ethiopic script) text renders correctly
        in the Lead Activity Report PDF instead of showing ???.
        Uses an Ethiopic-capable font (Noto Sans Ethiopic) for report output.
    """,
    'author': 'Temer Properties',
    'website': 'https://yourcompany.com',
    'depends': ['web', 'temer_crm'],
    'data': [
        'reports/temer_lead_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
