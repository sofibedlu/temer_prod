# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyReservation(models.Model):
    _inherit = "property.reservation"

    def cancel_reservation(self):
        """Block cancellation only if reservation is sold."""
        self.ensure_one()
        if self.status == 'sold':
            raise ValidationError(
                _("This reservation cannot be cancelled because it is already sold.")
            )
        if self.property_id and self.property_id.state == 'sold':
            raise ValidationError(
                _("This reservation cannot be cancelled because the property is already sold.")
            )
        return super().cancel_reservation()

    def action_open_reassign_wizard(self):
        """Open the reassign wizard for Show All users."""
        self.ensure_one()
        team_user_ids = self.env["reservation.contact.team"].sudo().search(
            [("is_active", "=", True)]
        ).mapped("user_id").filtered(
            lambda u: u.id != self.assigned_user_id.id
        ).ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Reassign Reservation"),
            "res_model": "reservation.reassign.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_reservation_id": self.id,
                "default_current_user_id": self.assigned_user_id.id,
                "default_contract_team_user_ids": [(6, 0, team_user_ids)],
            },
        }

    def action_assigned_sold(self):
        """For the assigned contract admin: convert reservation to sale."""
        for rec in self:
            if rec.assigned_user_id and rec.assigned_user_id != rec.env.user:
                raise ValidationError(
                    _(
                        "Only the assigned Contract Admin user (%s) can mark this reservation as Sold."
                    )
                    % rec.assigned_user_id.name
                )
            if rec.status != "sales_confirmed":
                raise ValidationError(
                    _("You can only sell reservations with Status = Sales Confirmed.")
                )
            # # Block if no payment has been verified yet
            # verified = rec.payment_line_ids.filtered(lambda p: p.is_verifed)
            # if not verified:
            #     raise ValidationError(
            #         _("Payment must be verified before marking this reservation as Sold.")
            #     )
            rec.sudo().sale_property_reserved()
            return {"type": "ir.actions.client", "tag": "reload"}

