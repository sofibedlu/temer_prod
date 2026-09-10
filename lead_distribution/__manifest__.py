{
    "name": "Lead Distribution",
    "version": "17.0.1.0.0",
    "summary": "Consolidated View for Sent leads from multiple sources",
    "category": "Sales/CRM",
    "author": "Kasahun Ybeltal",
    "depends": ["crm", "mail", "crm_custom_menu"],
    "data": [
        "security/lead_distribution_security.xml",
        "security/ir.model.access.csv",
        "views/lead_distribution_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
