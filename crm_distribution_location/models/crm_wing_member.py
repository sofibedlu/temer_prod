# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmWingMember(models.Model):
    _inherit = "crm.wing.member"

    location_id = fields.Many2one(
        "property.distribution.location",
        string="Location",
        required=True,
        ondelete="restrict",
        default=lambda self: self._default_location_id(),
    )

    @api.model
    def _default_location_id(self):
        return self.env.ref(
            "crm_distribution_location.distribution_location_head_office",
            raise_if_not_found=False,
        )

    @api.model_create_multi
    def create(self, vals_list):
        default_loc = self._default_location_id()
        for vals in vals_list:
            if not vals.get("location_id") and default_loc:
                vals["location_id"] = default_loc.id
        return super().create(vals_list)
