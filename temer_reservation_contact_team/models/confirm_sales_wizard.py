# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ConfirmSalesMessageWizard(models.TransientModel):
    _name = "reservation.confirm.sales.wizard"
    _description = "Confirm Sales Message"

    message = fields.Text(readonly=True)
    reservation_id = fields.Many2one("property.reservation", readonly=True)

    def action_ok(self):
        """Close popup and reopen the reservation form so UI shows updated status."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reservation"),
            "res_model": "property.reservation",
            "res_id": self.reservation_id.id,
            "view_mode": "form",
            "target": "current",
        }
