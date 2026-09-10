{
    'name': 'Temer CRM Structure',
    'version': '17.0.1.0.0',
    'summary': 'Temer CRM  Structure',
    'description': """
       Temer CRM Structure
        ==============================
    """,
    'category': 'Sales',
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 'crm','calendar',
        'advanced_property_management','ahadubit_property_reservation','ahadubit_crm','contract_sections' ,'ahadubit_property_base',
         'sale_crm','sales_team','temer_crm',
          'mail' # Example: if you have a custom property management module
    ],
    'data': [
        'views/views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
