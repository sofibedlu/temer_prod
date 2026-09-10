# -*- coding: utf-8 -*-
{
    'name': 'Custom Report Wizard - Dynamic Wing Selection',
    'version': '17.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Make wing selection dynamic from database for custom report wizard',
    'description': """
        Custom Report Wizard - Dynamic Wing Selection
        =============================================
        This module extends the custom_report_wizard module to make wing selection
        dynamic by fetching all wings from the property_sales_wing table instead
        of hardcoded values.
        
        Features:
        * Dynamically fetches all wings from database
        * Shows all wings including "Agent" and "No wing"
        * No hardcoded wing names
        * Works with all three wizards: Temer Lead Analysis, Lead Analysis, Team Activity
    """,
    'author': 'Selenat Alemerew',
    'depends': [
        'base',
        'custom_report_wizard',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

