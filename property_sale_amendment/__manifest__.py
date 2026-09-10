{
    "name": "Property Sale Amendment",
    "version": "1.0.0",
    "summary": "Add Updates to property sale orders and related workflows",
    "author": "Sofonias B/Temerproperties",
    "license": "LGPL-3",
    "depends": ["base",
                "advanced_property_management",
                "ahadubit_property_base"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizards/property_sale_update.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False
}