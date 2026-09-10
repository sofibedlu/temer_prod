{
    "name": "CRM Menu Access Control",
    "version": "1.0",
    "summary": "Restrict CRM menus so each role only sees their own menu",
    "category": "Operations",
    "author": "Temer",
    "depends": ["crm_custom_menu"],
    "data": [
        "security/crm_menu_groups.xml",
        "views/crm_menu_override.xml",
    ],
    "installable": True,
    "application": False,
}
