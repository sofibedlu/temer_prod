# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PropertyReservationValidation(models.Model):
    _inherit = 'property.reservation'

    @api.constrains('property_id', 'reservation_type_id', 'status')
    def _check_property_reservation_unique(self):
        """
        Validate that one property can only have one active reservation.
        This validation applies to ALL reservation types: Quick, Regular, and Special.
        A property can only be reserved once, regardless of reservation type.
        """
        for rec in self:
            # Skip validation if reservation_type_id or property_id is not set
            if not rec.reservation_type_id or not rec.property_id:
                continue

            # Check for existing active reservations of ANY type (Quick, Regular, or Special)
            # Only 'reserved' status is considered active - 'requested' status allows property to remain available
            # 'draft', 'pending_sales', 'canceled', 'expired', and 'sold' are not blocking
            domain = [
                ('id', '!=', rec.id),
                ('property_id', '=', rec.property_id.id),
                ('status', '=', 'reserved')
            ]

            existing_reservation = self.search(domain, limit=1)
            if existing_reservation:
                try:
                    existing_type = existing_reservation.reservation_type_id.reservation_type
                    existing_type_name = existing_reservation.reservation_type_id.name or existing_type
                except Exception:
                    existing_type_name = 'another'
                
                raise ValidationError(
                    _('This property already has an active reservation (%s). '
                      'Only one active reservation is allowed per property, regardless of type (Quick, Regular, or Special). '
                      'Please cancel or wait for the existing reservation to expire before creating a new one.') % 
                      (existing_type_name,)
                )

