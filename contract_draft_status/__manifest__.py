# -*- coding: utf-8 -*-
{
    "name": "Contract Draft Status",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "Adds draft_status to draft.contract.archive and controls wizard content source",
    "author": "Temer Properties",
    "depends": ["draft_archive_model", "contract_managment", "receipt_dashboard", "contract_archive_edited", "contract_pdf_preview"],
    "data": [
        "security/ir.model.access.csv",
        "views/draft_archive_status_views.xml",

    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
