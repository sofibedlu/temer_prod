# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyReservation(models.Model):
    _inherit = "property.reservation"

    assigned_user_id = fields.Many2one(
        "res.users",
        string="Assigned To",
        tracking=True,
    )
    # Extend the core status with a Sales Confirmed state
    status = fields.Selection(
        selection_add=[("sales_confirmed", "Sales Confirmed")],
        ondelete={"sales_confirmed": "set default"},
    )
    is_quick_reservation = fields.Boolean(
        compute="_compute_is_quick_reservation",
        string="Is Quick Reservation",
    )

    def _compute_is_quick_reservation(self):
        for rec in self:
            rec.is_quick_reservation = (
                rec.reservation_type_id.reservation_type == 'quick'
                if rec.reservation_type_id else False
            )

    def action_confirm_sales(self):
        """Assign reservation to a contract admin without creating the sale."""
        for rec in self:
            if rec.status != "reserved":
                raise ValidationError(
                    _("You can only confirm sales for reservations in Reserved status.")
                )

            # Block if payment is required but not verified
            if rec.is_payment_required:
                if not rec.payment_line_ids:
                    raise ValidationError(
                        _("Please  verify the payment first before confirming sales.")
                    )
                verified = rec.payment_line_ids.filtered(lambda p: p.is_verifed)
                if not verified:
                    raise ValidationError(
                        _("Please verify the payment first before confirming sales.")
                    )

            # Find the first "new" active contract admin user (sudo: caller may not have contact team access)
            ContactTeam = self.env["reservation.contact.team"].sudo()
            contact_line = ContactTeam.search([("status", "=", "new"), ("is_active", "=", True)], limit=1, order="create_date asc")
            if not contact_line:
                # All active members are served; reset only active ones back to New and start again
                all_active = ContactTeam.search([("is_active", "=", True)])
                all_active.write({"status": "new"})
                contact_line = ContactTeam.search([("status", "=", "new"), ("is_active", "=", True)], limit=1, order="create_date asc")
            if not contact_line:
                raise ValidationError(
                    _(
                        "No available active Contract Admin user found.\n"
                        "Please configure at least one active Contract Admin member with status New "
                        "under Property → Configuration → Reservation → Contract Admin Team."
                    )
                )

            # Assign and update statuses
            rec.assigned_user_id = contact_line.user_id
            rec.status = "sales_confirmed"
            contact_line.status = "served"

            # Move property to pending_sales so the expiry cron cannot free it back to available
            if rec.property_id and rec.property_id.state not in ('sold', 'pending_sales'):
                rec.property_id.sudo().write({'state': 'pending_sales'})

            # Notify assigned user on the reservation
            if rec.assigned_user_id.partner_id:
                rec.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=rec.assigned_user_id.id,
                    summary=_("Reservation assigned for contract preparation"),
                    note=_(
                        "You have been assigned as Contract Admin for reservation of property %s "
                        "for customer %s. Please go to Reservation → Assigned Sales to continue."
                    )
                    % (rec.property_id.display_name, rec.partner_id.display_name),
                )

            # Reopen form to show updated status
            return {
                "type": "ir.actions.act_window",
                "name": _("Reservation"),
                "res_model": "property.reservation",
                "res_id": rec.id,
                "view_mode": "form",
                "target": "current",
            }
        return True

    def check_expired_reservation(self):
        """Override to prevent sales_confirmed reservations from being expired by the cron."""
        # Temporarily exclude sales_confirmed from expiry processing
        # by marking them so the base/super won't touch them
        sales_confirmed = self.search([
            ('status', '=', 'sales_confirmed'),
            ('expire_date', '<=', fields.Datetime.now()),
        ])
        # Extend their expire_date temporarily so super() skips them,
        # then restore — actually just call super and re-protect after
        result = super().check_expired_reservation()
        # If super() accidentally expired any sales_confirmed, restore them
        wrongly_expired = self.search([
            ('status', '=', 'expired'),
            ('id', 'in', sales_confirmed.ids),
        ])
        for res in wrongly_expired:
            res.sudo().write({'status': 'sales_confirmed'})
            if res.property_id and res.property_id.state == 'available':
                res.property_id.sudo().write({'state': 'reserved'})
        return result

