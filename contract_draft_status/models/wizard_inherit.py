# -*- coding: utf-8 -*-
import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class ContractPreviewWizardDraftStatus(models.TransientModel):
    _inherit = "contract.preview.wizard"

    def _get_draft_for_sale(self):
        """Find the active draft.contract.archive for this sale."""
        sale = self.sale_id
        return (
            self.env["draft.contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
            )
        )

    def action_save_to_archive(self):
        """Mark draft_status = 'saved' after the super chain saves to contract.archive."""
        self.ensure_one()
        result = super().action_save_to_archive()
        draft = self._get_draft_for_sale()
        if draft:
            draft.write({"draft_status": "saved"})
            _logger.info(
                "action_save_to_archive: draft id=%s marked 'saved' for sale=%s",
                draft.id, self.sale_id.name,
            )
        return result

    def _inject_pdf_watermark(self, action):
        """Inject CSS watermark into the report action data if draft."""
        draft = self._get_draft_for_sale()
        if draft and draft.draft_status == "draft" and isinstance(action, dict) and "data" in action:
            html_content = action["data"].get("full_content", "")
            if html_content:
                # Use a <style> block targeting .page::after so wkhtmltopdf repeats it on every page
                watermark_style = """
                <style>
                    .page::after {
                        content: "DRAFT CONTRACT";
                        position: fixed;
                        top: 500px;
                        left: -50%;
                        width: 200%;
                        text-align: center;
                        transform: rotate(-45deg);
                        font-size: 80pt;
                        color: rgba(192, 192, 192, 0.25);
                        font-weight: bold;
                        z-index: 9999;
                        pointer-events: none;
                        white-space: nowrap;
                        font-family: Arial, sans-serif;
                        display: block;
                    }
                </style>
                """
                from markupsafe import Markup
                action["data"]["full_content"] = Markup(watermark_style + str(html_content))
        return action

    def action_print_pdf(self):
        action = super().action_print_pdf()
        return self._inject_pdf_watermark(action)

    def action_download_pdf(self):
        action = super().action_download_pdf()
        return self._inject_pdf_watermark(action)
