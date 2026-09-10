# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class ReservationReassignWizard(models.TransientModel):
    _name = "reservation.reassign.wizard"
    _description = "Reassign Reservation to Another Contract Team Member"

    reservation_id = fields.Many2one(
        "property.reservation",
        string="Reservation",
        required=True,
        readonly=True,
    )
    current_user_id = fields.Many2one(
        "res.users",
        string="Currently Assigned To",
        readonly=True,
    )
    new_user_id = fields.Many2one(
        "res.users",
        string="Reassign To",
        required=True,
    )
    contract_team_user_ids = fields.Many2many(
        "res.users",
        "reassign_wizard_user_rel",
        "wizard_id",
        "user_id",
        string="Contract Team Users",
    )
    remark = fields.Text(
        string="Remark",
        help="Optional note about why this reassignment is being made.",
    )

    def action_reassign(self):
        self.ensure_one()
        reservation = self.reservation_id
        if not reservation:
            raise ValidationError(_("No reservation found."))
        if self.new_user_id == self.current_user_id:
            raise ValidationError(_("The new assignee is the same as the current one."))

        old_user = reservation.assigned_user_id
        new_user = self.new_user_id

        note_parts = [
            _("Reservation reassigned from <b>%s</b> to <b>%s</b>.")
            % (
                old_user.name if old_user else _("(none)"),
                new_user.name,
            )
        ]
        if self.remark:
            note_parts.append(_("Remark: %s") % self.remark)

        reservation.sudo().write({"assigned_user_id": new_user.id})
        reservation.sudo().message_post(
            body=" ".join(note_parts),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}
