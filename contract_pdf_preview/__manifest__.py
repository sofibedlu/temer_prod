{
    "name": "Contract PDF Preview",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "PDF preview and download for contracts using Odoo report engine",
    "author": "Kasahun ybeltal",
    "depends": ["contract_managment"],
    "data": [
        "security/ir.model.access.csv",
        "views/contract_pdf_report.xml",
        "views/wizard_inherit.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
