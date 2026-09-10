{
    "name": "Draft Archive Model",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "Draft contract archive — clone of contract.archive for draft editing",
    "author": "Kasahun ybeltal",
    "depends": ["contract_managment", "contract_pdf_preview"],
    "data": [
        "security/ir.model.access.csv",
        "views/draft_archive_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
