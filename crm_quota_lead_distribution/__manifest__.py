# -*- coding: utf-8 -*-
{
    "name": "CRM Quota Lead Distribution",
    "version": "17.0.1.9.28",
    "summary": "Quota lead assignment, rotation, duplicates, SMS via Login",
    "category": "Sales/CRM",
    "author": "Temer Properties",
    "depends": [
        "crm_custom_menu",
        "crm_custom_menu_customer_phone",
        "advanced_property_management",
        "temer_structure",
        "temer_crm",
    ],
    "sequence": 500,
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_distribution_menus.xml",
        "views/crm_lead_quota_views.xml",
        "views/crm_wing_member_views.xml",
        "wizard/crm_lead_duplicate_message_wizard_views.xml",
        "views/crm_lead_distribution_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "crm_quota_lead_distribution/static/src/js/duplicate_message_wizard.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
