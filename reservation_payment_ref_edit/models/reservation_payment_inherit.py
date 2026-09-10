# -*- coding: utf-8 -*-
from lxml import etree
from odoo import models, fields, api

PRIVILEGED_ONLY_STATUSES = {"sales_confirmed", "sold", "pending_sales"}
LOCKED_STATUSES = {"canceled", "expired"}
PRIVILEGED_GROUPS = [
    "receipt_dashboard.group_receipt_dashboard_user",
    "receipt_dashboard.group_receipt_dashboard_manager",
    "temer_structure.access_property_contract_admin_group",
    "temer_structure.access_property_super_admin_group",
]


class PropertyReservationPaymentRefEdit(models.Model):
    _inherit = "property.reservation"

    @api.model
    def get_views(self, views, options=None):
        result = super().get_views(views, options)
        user = self.env.user
        is_privileged = (
            any(user.has_group(g) for g in PRIVILEGED_GROUPS)
            or user._is_admin()
        )
        for view_type, view_data in result.get("views", {}).items():
            if view_type != "form":
                continue
            arch_str = view_data.get("arch")
            if not arch_str:
                continue
            try:
                arch = etree.fromstring(arch_str)
            except Exception:
                continue

            modified = False

            # Lock payment_line_ids readonly for non-privileged on locked statuses
            # We can't know the record status at view-load time, so we handle this
            # via the readonly attribute using status field which IS in the view
            for node in arch.xpath("//field[@name='payment_line_ids']"):
                # Add readonly based on status using existing status field
                # For non-privileged: lock on pending_sales/sold/sales_confirmed/canceled/expired
                # For privileged: only lock on canceled/expired
                if not is_privileged:
                    existing = node.get("readonly", "")
                    lock_expr = "status in ['sales_confirmed','sold','pending_sales','canceled','expired']"
                    if existing and existing != "0" and existing != "False":
                        node.set("readonly", "(%s) or (%s)" % (existing, lock_expr))
                    else:
                        node.set("readonly", lock_expr)
                    modified = True

            if modified:
                view_data["arch"] = etree.tostring(arch, encoding="unicode")

        return result


class PropertyReservationPayment(models.Model):
    _inherit = "property.reservation.payment"

    ref_editable = fields.Boolean(
        string="Reference Editable",
        compute="_compute_ref_editable",
    )

    @api.depends("reservation_id.status")
    @api.depends_context("uid")
    def _compute_ref_editable(self):
        for rec in self:
            if not rec.id:
                # New unsaved line — always editable
                rec.ref_editable = True
                continue
            if rec.reservation_id.status not in ("reserved", "sales_confirmed"):
                rec.ref_editable = False
                continue
            # Reserved or Sales Confirmed: editable only if no approval record or approval is still draft
            approval = self.env["receipt.approval.record"].sudo().search(
                [("payment_line_id", "=", rec.id)], limit=1
            )
            rec.ref_editable = not approval or approval.state == "draft"

    def write(self, vals):
        old_refs = {}
        if "ref_number" in vals:
            for rec in self:
                old_refs[rec.id] = rec.ref_number
        result = super().write(vals)
        if "ref_number" in vals:
            for rec in self:
                old_ref = old_refs.get(rec.id, "")
                new_ref = rec.ref_number or ""
                if old_ref == new_ref:
                    continue
                approvals = self.env["receipt.approval.record"].sudo().search(
                    [("payment_line_id", "=", rec.id)]
                )
                if approvals:
                    new_filename = ("Receipt_%s.pdf" % new_ref) if new_ref else "Receipt.pdf"
                    self.env.cr.execute(
                        "UPDATE receipt_approval_record SET reference_number = %s, payment_receipt_filename = %s WHERE id = ANY(%s)",
                        (new_ref or None, new_filename, approvals.ids),
                    )
                    approvals.invalidate_recordset(["reference_number", "payment_receipt_filename"])
                if rec.reservation_id:
                    rec.reservation_id.message_post(
                        body="Reference updated by %s: %s -> %s" % (
                            self.env.user.name, old_ref or "(empty)", new_ref or "(empty)"),
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )
        return result