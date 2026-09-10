# -*- coding: utf-8 -*-
{
    "name": "Contract Archive Reset on Confirm",
    "version": "17.0.1.0.0",
    "category": "Sales/Contracts",
    "summary": "On action_confirm: delete existing contract.archive and draft.contract.archive, then recreate both fresh",
    "author": "Temer Properties",
    "depends": ["contract_managment", "draft_archive_model"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
