# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models


class CrmLeadDuplicateMessageWizard(models.TransientModel):
    _name = "crm.lead.duplicate.message.wizard"
    _description = "Duplicate Phone Message"

    lead_model = fields.Char(readonly=True)
    lead_res_id = fields.Integer(readonly=True)
    title = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    message_html = fields.Html(compute="_compute_message_html", sanitize=False)
    is_inactive_salesperson = fields.Boolean(readonly=True)
    existing_salesperson_id = fields.Many2one("res.users", readonly=True)
    existing_supervisor_id = fields.Many2one(
        "property.sales.supervisor", readonly=True
    )
    existing_salesperson_phone = fields.Char(readonly=True)

    @api.depends("message")
    def _compute_message_html(self):
        for wiz in self:
            lines = [
                line.strip()
                for line in (wiz.message or "").replace("\r", "").split("\n")
                if line.strip()
            ]
            if not lines and (wiz.message or "").strip():
                lines = [(wiz.message or "").strip()]
            wiz.message_html = (
                "".join("<p class=\"mb-2\">%s</p>" % line for line in lines)
                if lines
                else ""
            )

    @staticmethod
    def _normalize_message(msg):
        """One line per registration source (readable in popup)."""
        if not msg:
            return ""
        text = msg.replace("\r", "").strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) > 1:
            return "\n".join(lines)
        parts = re.split(r"(?<=\.)\s+", text)
        parts = [p.strip() for p in parts if p.strip()]
        return "\n".join(parts) if parts else text

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        model = self.env.context.get("default_lead_model")
        res_id = self.env.context.get("default_lead_res_id")
        if not model or not res_id or model not in self.env:
            return res
        lead = self.env[model].browse(res_id).exists()
        if not lead:
            return res
        msg = self._normalize_message(
            lead.phone_number_message or getattr(lead, "status", "") or ""
        )
        inactive = bool(getattr(lead, "reassign_lead", False))
        res.update(
            {
                "lead_model": model,
                "lead_res_id": res_id,
                "message": msg,
                "is_inactive_salesperson": inactive,
                "title": (
                    _("Inactive salesperson — use Reassign")
                    if inactive
                    else _("Existing customer")
                ),
                "existing_salesperson_id": lead.existing_salesperson_id.id,
                "existing_supervisor_id": lead.existing_supervisor_id.id,
                "existing_salesperson_phone": getattr(
                    lead, "existing_salesperson_phone", ""
                )
                or "",
            }
        )
        return res

    def action_close(self):
        self.ensure_one()
        if (
            self.lead_model
            and self.lead_res_id
            and self.lead_model in self.env
        ):
            self.env[self.lead_model].browse(self.lead_res_id).write(
                {"quota_duplicate_popup_pending": False}
            )
        return {"type": "ir.actions.act_window_close"}
