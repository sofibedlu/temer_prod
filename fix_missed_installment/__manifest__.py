{
    "name": "Fix Missed Installment",
    "summary": "Standalone tool to fix missed installment substitutions",
    "version": "17.0.2.0.0",
    "author": "Temerproperties",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": [
        "base",
        "installment_update",
        "collection_management",
        "advanced_property_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fix_missed_installment_wizard_views.xml",
        "views/fix_missed_installment_log_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
