{
    "name": "Contract Log Message",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "Adds message logging to contract actions",
    "description": "This module inherits from draft_archive_model to add chatter messages whenever a contract is printed, saved to archive, or downloaded as DOCX.",
    "author": "Kasahun Ybeltal",
    "depends": ["draft_archive_model", "contract_managment", "mail"],
    "data": [
        "views/contract_section_article_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
