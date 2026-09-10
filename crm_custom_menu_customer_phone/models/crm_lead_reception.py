# -*- coding: utf-8 -*-

from odoo import api, models

from . import crm_customer_phone_mixin as phone_util


class CrmReceptionCustomerPhone(models.Model):
    _inherit = "crm.reception"

    @api.model_create_multi
    def create(self, vals_list):
        pending = []
        for vals in vals_list:
            pending.append(
                phone_util.get_new_phone_entry(self, vals) if vals.get("new_phone") else None
            )
        records = super().create(vals_list)
        for rec, entry in zip(records, pending):
            if entry:
                phone_util.replace_wrong_country_phone_lines(rec, entry)
        phone_util.sync_phone_lines_country(records)
        return records

    def write(self, vals):
        saved_phone_ids = {}
        phone_entry = None
        if vals.get("new_phone"):
            phone_entry = phone_util.get_new_phone_entry(self, vals)
            if phone_entry:
                for rec in self:
                    saved_phone_ids[rec.id] = list(rec.full_phone.ids)

        res = super().write(vals)

        if phone_entry and saved_phone_ids:
            for rec in self:
                phone_util.merge_full_phone_entry(
                    rec, phone_entry, saved_ids=saved_phone_ids.get(rec.id)
                )
                phone_util.replace_wrong_country_phone_lines(rec, phone_entry)

        if vals.get("new_phone") or vals.get("country_id"):
            phone_util.sync_phone_lines_country(self)
        return res
