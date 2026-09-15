{
    "name": "Temer Hotfixes",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "Sofonias B/TemerProperties",
    "summary": "Collection of hotfixes for TemerProperties modules",
    "depends": [
        "ahadubit_property_base",
        "advanced_property_management",
        "ahadubit_property_reservation",
        "temer_payment_modify",
        "property_legacy_data",
        "collection_management",
        "contract_sections",
        "temer_structure",
        "property_contract_extension",
        "property_sale_audited_state",
    ],
    "data": [
        "views/property_sale_payment_schedule.xml",
        "views/property_block_fix.xml",
    ],
    'external_dependencies': {
        'python': ['ethiopian_date', 'ethioqen'],
    },
    "installable": True,
    "application": False,
}