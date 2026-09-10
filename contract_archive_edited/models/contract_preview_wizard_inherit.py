import re
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class ContractPreviewWizardArchiveEdit(models.TransientModel):
    _inherit = "contract.preview.wizard"

    def _get_archive(self):
        """Find the active archive for this sale."""
        sale = self.sale_id
        return (
            self.env["contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["contract.archive"].search(
                [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
            )
            or (
                sale.contract_id and self.env["contract.archive"].search(
                    [("name", "=", sale.contract_id.name), ("status", "!=", "void")], limit=1
                )
            )
        )

    def action_save_to_archive(self):
        """
        Write the edited preview_html back to the contract archive.
        - Saves to archive.rendered_html (used by print/preview controllers)
        - Also splits the HTML back into individual article lines and updates
          each article's content field so the archive stays in sync
        """
        self.ensure_one()
        
        if self.sale_id and self.sale_id.reservation_id:
            unapproved_receipts = self.env['receipt.approval.record'].sudo().search([
                ('reservation_id', '=', self.sale_id.reservation_id.id),
                ('state', '!=', 'approved')
            ])
            if unapproved_receipts:
                raise UserError(_("Cannot save Contract to archive. All receipts for this reservation must be approved."))

        if not self.preview_html:
            raise UserError(_("No content to save."))

        archive = self._get_archive()
        if not archive:
            raise UserError(_("No Contract Archive found for this sale."))

        html_str = str(self.preview_html)

        # 1. Save full rendered HTML to archive.rendered_html
        archive.write({"rendered_html": Markup(html_str)})

        # 2. Split back into contract-section divs and update article lines
        section_contents = re.findall(
            r'<div class="contract-section"[^>]*>(.*?)</div>\s*(?=<div class="contract-section"|$)',
            html_str,
            re.DOTALL,
        )

        if section_contents:
            active_articles = archive.article_ids.filtered(
                lambda a: a.is_active and a.content
            ).sorted("sequence")

            for article, new_content in zip(active_articles, section_contents):
                cleaned = new_content.strip()
                if cleaned and cleaned != str(article.content or "").strip():
                    article.write({"content": Markup(cleaned)})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Saved"),
                "message": _("Contract edits saved to archive successfully."),
                "type": "success",
                "sticky": False,
            },
        }
