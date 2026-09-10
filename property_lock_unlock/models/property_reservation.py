# -*- coding: utf-8 -*-
##############################################################################
#    Property Lock / Unlock
#    Copyright (C) 2024-TODAY Ahadubit Technologies
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    # Override domain to exclude locked properties from reservation
    property_id = fields.Many2one(
        'property.property',
        domain=[('state', 'in', ['available']), ('is_locked', '=', False)],
        string="Property",
        required=True,
        tracking=True
    )

    @api.constrains('property_id')
    def _check_property_not_locked(self):
        for rec in self:
            if rec.property_id and rec.property_id.is_locked:
                raise ValidationError(
                    _("Cannot reserve a locked property: %s") % rec.property_id.name
                )
