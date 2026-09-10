# -*- coding: utf-8 -*-
{
    "name": "CRM Distribution Location",
    "version": "17.0.1.0.25",
    "summary": "Walk-in reception location filters distribution members",
    "category": "Sales/CRM",
    "author": "Temer Properties",
    "depends": [
        "crm_custom_menu",
        "crm_quota_lead_distribution",
        "advanced_property_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/property_distribution_location_data.xml",
        "views/property_distribution_location_views.xml",
        "views/crm_wing_member_views.xml",
        "views/crm_reception_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
