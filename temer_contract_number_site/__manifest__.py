{
    "name": "Temer Contract Number by Site",
    "version": "17.0.1.0.0",
    "author": "Sofonias B/Temerproperties",
    "summary": "Contract number COMPANY/LOCATION/SITE/TYPE/SEQ/YY + auto template by company and site",
    "depends": [
        "base",
        "contract_sections",
        "ahadubit_property_base",
        "ahadubit_property_base_custom",
        "property_type_office",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/contract_template_inherit_views.xml",
        "views/site_company_mapping_views.xml",
        "views/site_location_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}