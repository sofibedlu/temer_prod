{
    'name': 'Temer Term Line Data Repair',
    'version': '17.0.1.0.0',
    'author': 'Sofonias B/Temerproperties',
    'summary': 'Repairs NULL payment_term_id values in property.payment.term.line',
    'depends': ['ahadubit_property_base', 'advanced_property_management'], 
    'data': [
        'security/ir.model.access.csv',
        'views/repair_wizard_views.xml',
        'views/payment_term_views.xml',
    ],
    'installable': True,
    'application': False,
}