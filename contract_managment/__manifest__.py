{
    "name": "Contract Managment",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "Manage contracts",
    "description": """
        This module allows you to manage contract .
        You can create, edit, and organize different contracts.
    """,
    "author": "Kasahun ybeltal",
    "depends": [
        "base",
        "mail",
        "web",
        "advanced_property_management",
        "ahadubit_property_reservation",
        "contract_sections",
        "property_contract_extension"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/contract_inherited_field.xml",
        "reports/paperformat_data.xml",
        "views/contract_archive_views.xml",
        "views/property_sale_action_views.xml",
        "reports/contract_report.xml",
        "views/contract_template_view.xml",
        "views/contract_preview_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "assets": {
        "web.assets_backend": [
            "contract_sections/static/src/css/contract_style.css",
        ],
    },
}
