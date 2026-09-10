# -*- coding: utf-8 -*-
from odoo import api, models

from .crm_lead_distribution import CrmLeadDistribution


class CrmReception(models.Model):
    _name = "crm.reception"
    _inherit = ["crm.reception", "crm.lead.distribution", "crm.channel.notify.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        return self._quota_create_records(vals_list)

    def _get_next_available_rr_user_and_config(self):
        return self._quota_assign_next_user()

    def _create_temer_lead_automatically(self):
        return self._create_temer_lead_after_sms()

    def _send_sms_for_duplicate(self):
        return self._quota_apply_duplicate()

    def _wing_create_lead_and_send_sms(self, phone_override=None):
        return self._create_temer_lead_after_sms()

    def _send_sms_to_existing_sales_team(self):
        self.ensure_one()
        return self._send_sales_team_sms_from_record(
            source="Walk In",
            is_existing=True,
            lead=self,
        )

    @api.constrains("source_id")
    def _check_source_id(self):
        """Allow reception users to pick or create any utm.source (wing-era UX)."""
        return

    def write(self, vals):
        if self.env.context.get("quota_treat_as_new"):
            return self._write_skip_crm_custom_menu(vals)
        return super(CrmLeadDistribution, self).write(vals)
