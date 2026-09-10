from odoo import models, fields, api, _
from odoo.tools import Markup


class PaymentApprovalRecord(models.Model):
    _inherit = "payment.approval.record"

    requested_by_id = fields.Many2one(
        "res.users",
        string="Initiated By",
        readonly=True,
        tracking=True,
    )
    requested_by_partner_id = fields.Many2one(
        "res.partner",
        related="requested_by_id.partner_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        initiator_uid = self.env.context.get("payment_requested_by_uid")
        for vals in vals_list:
            if not vals.get("requested_by_id") and initiator_uid:
                vals["requested_by_id"] = initiator_uid

        records = super().create(vals_list)
        return records

    def _notify_initiator(self, title, body):
        for rec in self:
            partner = rec.requested_by_partner_id
            if not partner:
                continue
            
            target = rec.collection_id or rec
            target.sudo().message_subscribe(partner_ids=[partner.id])
            target.sudo().message_post(
                subject=title,
                body=body,
                message_type="notification",
                partner_ids=[partner.id],
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid="mail.mail_notification_light",
            )

    def write(self, vals):
        old_state_by_id = {}
        if "state" in vals:
            for rec in self:
                old_state_by_id[rec.id] = rec.state

        res = super().write(vals)

        if "state" not in vals:
            return res

        for rec in self:
            old_state = old_state_by_id.get(rec.id)
            new_state = rec.state

            if old_state == new_state:
                continue

            if new_state == "approved":
                invoice_name = rec.invoice_id.display_name if rec.invoice_id else _("N/A")
                reason = ""
                title = _("Payment Approved")
                body = Markup(
                    "<b>Payment Approved</b><br/>"
                    "Installment: %s<br/>"
                    "Amount: %s<br/>"
                    "Payment Date: %s<br/>"
                    "Reference: %s<br/>"
                    "Invoice: %s%s"
                ) % (
                    rec.installment_id.display_name if rec.installment_id else _("N/A"),
                    rec.amount,
                    rec.payment_date or _("N/A"),
                    rec.reference_number or rec.reference or _("N/A"),
                    invoice_name,
                    reason,
                )

                self._notify_initiator(title, body)

            elif new_state == "denied":
                title = _("Payment Denied")
                body = Markup(
                    "<b>Payment Denied</b><br/>"
                    "Installment: %s<br/>"
                    "Amount: %s<br/>"
                    "Payment Date: %s<br/>"
                    "Reference: %s<br/>"
                    "Reason: %s"
                ) % (
                    rec.installment_id.display_name if rec.installment_id else _("N/A"),
                    rec.amount,
                    rec.payment_date or _("N/A"),
                    rec.reference_number or rec.reference or _("N/A"),
                    rec.deny_reason or _("No reason provided"),
                )

                self._notify_initiator(title, body)

        return res