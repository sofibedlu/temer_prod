# -*- coding: utf-8 -*-

from odoo import models


def backfill_callcenter_phone_country(env):
    """Backfill country_id on crm.callcenter.phone from linked crm.callcenter leads."""
    try:
        IrConfig = env["ir.config_parameter"].sudo()
        key = "wing_distribution_configuration.phone_country_backfill_done"
        if IrConfig.get_param(key):
            return
        Phone = env["crm.callcenter.phone"].with_context(active_test=False)
        Lead = env["crm.callcenter"].with_context(active_test=False)
        phones_empty = Phone.search([("country_id", "=", False)])
        for phone in phones_empty:
            lead = Lead.search(
                [("full_phone", "in", phone.ids), ("country_id", "!=", False)],
                limit=1,
                order="write_date desc",
            )
            if lead:
                phone.country_id = lead.country_id.id
        IrConfig.set_param(key, "1")
    except Exception:
        pass  # If models not loaded yet, skip
