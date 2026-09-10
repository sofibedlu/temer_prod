# -*- coding: utf-8 -*-
{
    'name': 'Temer CRM Filters',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Enhanced filtering for Temer CRM Leads',
    'description': """
        This module extends the Temer CRM module with additional search filters
        for better lead management and filtering capabilities.
        
        Features:
        - Source-based filters (Call Center, Website, Affiliate)
        - Time-based filters (Today, Last 7 Days)
        - Enhanced Group By options
    """,
    'author': 'Temer Properties',
    'website': 'https://yourcompany.com',
    'depends': ['temer_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/temer_lead_search_filters.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

