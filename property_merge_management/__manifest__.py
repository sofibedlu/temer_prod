{
    "name": "Property Merge Management",
    "version": "17.0.1.1.4",
    "summary": "Merge properties (draft/available/reserved/pending sales) into one property",
    "category": "Real Estate",
    "author": "Temer",
    "depends": [
        "ahadubit_property_base",
        "ahadubit_property_reservation",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/property_merge_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "OPL-1",
}
