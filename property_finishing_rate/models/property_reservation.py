# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PropertyReservationFinishing(models.Model):
    _inherit = 'property.reservation'

    # Computed: 50% of commercial_amount (shown only for regular reservations on commercial properties)
    commercial_advance_amount = fields.Float(
        string="Required Advance (50%)",
        compute='_compute_commercial_advance',
        store=True,
        help="50% of the commercial amount — must be paid before reserving",
    )
    is_commercial_regular = fields.Boolean(
        compute='_compute_commercial_advance',
        store=True,
    )

    @api.depends('property_id', 'reservation_type_id')
    def _compute_commercial_advance(self):
        for rec in self:
            is_commercial = (
                rec.property_id
                and rec.property_id.property_type == 'commercial'
            )
            is_regular = (
                rec.reservation_type_id
                and rec.reservation_type_id.reservation_type == 'regular'
            )
            rec.is_commercial_regular = bool(is_commercial and is_regular)
            if rec.is_commercial_regular:
                rec.commercial_advance_amount = rec.property_id.commercial_amount * 0.5
            else:
                rec.commercial_advance_amount = 0.0

    def compute_expected_amount(self):
        """Override: for regular reservations on commercial properties,
        use 50% of commercial_amount as the required advance."""
        self.ensure_one()
        is_commercial = (
            self.property_id
            and self.property_id.property_type == 'commercial'
        )
        is_regular = (
            self.reservation_type_id
            and self.reservation_type_id.reservation_type == 'regular'
        )
        if is_commercial and is_regular and self.property_id.commercial_amount:
            return self.property_id.commercial_amount * 0.5

        # Fall back to original logic for all other cases
        return super().compute_expected_amount()
