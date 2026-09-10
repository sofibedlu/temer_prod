# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CrmReception(models.Model):
    _inherit = "crm.reception"

    distribution_location_id = fields.Many2one(
        "property.distribution.location",
        string="Location",
        required=False,
        ondelete="restrict",
        default=lambda self: self.env.ref(
            "crm_distribution_location.distribution_location_head_office",
            raise_if_not_found=False,
        ),
        tracking=True,
        help="Walk-in only.\n"
        "New lead: quota algorithm among Distribution Members at this location.\n"
        "Existing customer: copied from the existing reception record for this phone.",
    )

    def _reception_location_id_for_assign(self):
        return self._resolve_reception_location_id()

    def _reception_should_assign_by_location(self):
        if self.env.context.get("lead_distribution_skip_assign"):
            return False
        if self.env.context.get("quota_treat_as_new"):
            return bool(self._resolve_reception_location_id())
        if len(self) == 1 and (
            self.existing_salesperson_id or (getattr(self, "status", None) or "").strip()
        ):
            return False
        return bool(self._resolve_reception_location_id())

    def action_reassign_lead(self):
        """Re Assign on reception respects the Location field on the form."""
        self.ensure_one()
        if self.distribution_location_id:
            return super(
                CrmReception,
                self.with_context(
                    distribution_location_id=self.distribution_location_id.id
                ),
            ).action_reassign_lead()
        return super().action_reassign_lead()

    def _get_next_available_rr_user_and_config(self):
        """
        Walk-in reception: same quota algorithm as other channels, filtered by
        Distribution Configuration members at the selected location.
        """
        if self._name == "crm.reception":
            if self.env.context.get("lead_distribution_skip_assign"):
                return super()._get_next_available_rr_user_and_config()
            if (
                len(self) == 1
                and not self.env.context.get("quota_treat_as_new")
                and (
                    self.existing_salesperson_id
                    or (getattr(self, "status", None) or "").strip()
                )
            ):
                return super()._get_next_available_rr_user_and_config()
            loc_id = self._resolve_reception_location_id()
            if not loc_id:
                raise ValidationError(
                    _(
                        "Please select a Location for this walk-in lead. "
                        "Assignment uses only Distribution Members at that location."
                    )
                )
            return super(
                CrmReception,
                self.with_context(distribution_location_id=loc_id),
            )._get_next_available_rr_user_and_config()
        return super()._get_next_available_rr_user_and_config()

    @api.model
    def _clear_legacy_reception_locations(self):
        """One-time: old reception rows should not show Head Office."""
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("crm_distribution_location.reception_locations_cleared"):
            return
        self.sudo().search([]).write({"distribution_location_id": False})
        ICP.set_param("crm_distribution_location.reception_locations_cleared", "1")
