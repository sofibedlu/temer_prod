{
    "name": "Bank Configuration Update",
    "summary": "Bank Configuration",
    "version": "17.0.1.0.0",
    "category": "Property  Management",
    "website": "https://yourcompany.com",
    "depends": ['advanced_property_management', 'contract_sections', 'ahadubit_property_base', 'mail',
                'ahadubit_property_reservation'],
    "data": [
        "security/ir.model.access.csv",
        "views/site_developer_on_site_view.xml",
        "views/payment_line_update.xml",
        "views/bank.xml",
        "data/data.xml", 'data/bank_configuration_data.xml',
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
