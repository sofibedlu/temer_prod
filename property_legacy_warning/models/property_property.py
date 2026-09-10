# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    def action_reserve(self):
        """Block reservation from the property form view."""
        for rec in self:
            if rec.is_legacy:
                raise ValidationError(
                    _("'%s' is a Legacy Property and cannot be reserved.") % rec.name
                )
        return super().action_reserve()


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    @api.constrains('property_id')
    def _check_legacy_property(self):
        """Block reservation from any entry point (CRM, property form, direct)."""
        for rec in self:
            if rec.property_id and rec.property_id.is_legacy:
                raise ValidationError(
                    _("'%s' is a Legacy Property and cannot be reserved.") % rec.property_id.name
                )
