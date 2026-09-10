# -*- coding: utf-8 -*-
{
    'name': "Ahadubit Real Estate Reservation",
    'version': '17.0.1.0.0',
    'summary': """
        Property reservation management system with advanced features
        """,
    'description': """
        Real Estate Reservation System Features:
        * Property reservation management
        * Special discount handling
        * Reservation history tracking
        * Cancellation management
        * Extension and transfer features
    """,

    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",

    'category': 'Sales',

    'depends': [
        'base',
        'crm',
        'ahadubit_property_base',
    ],

    'data': [

        
        'security/reservation_security.xml',
        'security/ir.model.access.csv',
        'data/reservation_data.xml',
        'data/reservation_cron.xml',
        # Views
        'views/reservation_special_discount.xml',
        'views/reservation_config_views.xml',
        'views/property_reservation_views.xml',
        'views/reservation_extension_views.xml',
        'wizard/cancellation_reason_wizard_views.xml',
        'wizard/payment_cancel_reason.xml',
        'views/reservation_transfer_views.xml',
        'data/menu.xml',
        #report
        'report/reservation_report.xml',
        'report/reservation_log_report.xml'


        

    ],
     'external_dependencies': {
        'python': ['pytesseract', 'opencv-python', 'Pillow', 'numpy','pdf2image','python-magic'],  # Add all required Python libraries
    },
    'images': ['static/description/icon.png'],
    'demo': [
       
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}