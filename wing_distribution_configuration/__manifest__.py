{
    "name": "Wing Distribution Configuration",
    "version": "1.1",
    "summary": "Weighted distribution for reception supervisor assignment",
    "category": "Operations",
    "author": "Temer",
    "depends": ["base", "base_setup", "crm_custom_menu", "crm_custom_menu_customer_phone", "temer_structure"],
    # Hooks disabled for now to avoid AttributeError during module install/upgrade.
    # If you need the migration logic from hooks.py, we can re-enable and debug separately.
    "data": [
        "views/wing_config_settings_views.xml",
        "security/wing_distribution_security.xml",
        "security/ir.model.access.csv",
        "data/wing_distribution_data.xml",
        "views/wing_distribution_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wing_distribution_configuration/static/src/css/customer_phones.css",
            "wing_distribution_configuration/static/src/js/reception_duplicate_notification.js",
            "wing_distribution_configuration/static/src/js/wing_distribution_list_reload.js",
        ],
    },
    "installable": True,
    "application": False,
}