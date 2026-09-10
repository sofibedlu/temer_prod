{
    'name': 'special reservation',
    'version': '1.0',
    'depends': ['ahadubit_property_reservation', 'crm_dashboard','contract_sections'],
    'data': [
        # 'data/ir_cron.xml',
        'security/special_reservation_groups.xml',
        'security/ir.model.access.csv',
        'views/property_reservation_history_view.xml',
        'report/report.xml',
        'report/report_special_approval_wizard_pdf.xml',
        # 'views/assets.xml',
     
    ],
    'assets': {
    'web.assets_backend': [
        'special_reservation/static/src/css/special_approval.css',
    ],
},

    'installable': True,
    'application': False,
}







