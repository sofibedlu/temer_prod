{
    'name': 'Temer Property Sales Structure',
    'version': '17.0.1.0.0',
    'summary': 'Temer Property Sales Structure',
    'description': """
       Temer Property Sales Structure
        ==============================
    """,
    'category': 'Sales',
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 'crm','calendar',
        'advanced_property_management','ahadubit_property_reservation','ahadubit_crm','contract_sections' ,'ahadubit_property_base',
         'sale_crm','sales_team',
          'mail' # Example: if you have a custom property management module
    ],
    'data': [
        'security/access_group.xml',
        'security/ir.model.access.csv',
        'views/views.xml',  
        'views/reservation.xml',
        'views/commision_view.xml',
        'views/self_access.xml',
        'data/commission_configuration_data.xml',
        'data/menus.xml',
        'views/crm.xml',
        'views/activity.xml',
        'reports/reservation_report.xml',
        
        'views/property_sale.xml'
    ],
    'assets': {
        'web.assets_backend': [
            # 'temer_structure/static/src/js/script.js',
            # 'temer_structure/static/src/js/form_access.js',
            'temer_structure/static/src/css/style.css',
        ],
           'web.assets_qweb': [
        'temer_structure/static/src/js/script.js',
    ],
    },
    'demo': [
      
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
