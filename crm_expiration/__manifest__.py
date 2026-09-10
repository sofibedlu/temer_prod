{
    'name': "CRM Lead Expiration",
    'version': '17.0.1.0.0',
    'summary': "Expire leads in CRM based on update time.",
    'author': "Eyuel",
    'website': "https://yourwebsite.com",
    'category': 'CRM',
    'depends': ['crm'],
    'data': [
        'data/ir_cron_dataa.xml',
        # 'views/crm_lead_view_inherted.xml'
    ],
    'installable': True,
    'auto_install': False,
}
