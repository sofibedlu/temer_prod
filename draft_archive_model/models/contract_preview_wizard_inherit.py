from odoo.exceptions import UserError
import logging
from odoo import models, api, _
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class ContractPreviewWizardDraftSave(models.TransientModel):
    _inherit = "contract.preview.wizard"

    def _get_draft_archive(self):
        """Find the draft.contract.archive linked to this sale."""
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

    def _get_or_create_draft_archive(self):
        """
        Find or create a draft.contract.archive for this sale.
        If none exists, create one from the current wizard state.
        """
        draft = self._get_draft_archive()
        if draft:
            return draft

        sale = self.sale_id

        # Try to clone from contract.archive
        source_archive = (
            self.env["contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["contract.archive"].search(
                [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
            )
        )

        if source_archive:
            draft = self.env["draft.contract.archive"].create_from_archive(source_archive.id)
        else:
            buyer = (
                sale.contract_id.person_ids.filtered(lambda p: p.person_type == "buyers")[:1]
                if sale.contract_id else None
            )
            customer_name = (
                f"{buyer.first_name or ''} {buyer.father_name or ''} {buyer.gfather_name or ''}".strip()
                if buyer else ""
            )
            draft = self.env["draft.contract.archive"].create({
                "sale_id":       sale.id,
                "customer_name": customer_name,
                "property_name": sale.property_id.name if sale.property_id else "",
                "sales_no":      sale.name or "",
                "status":        "active",
                "rendered_html": self.preview_html or "",
            })

        # Update rendered_html with current wizard content
        if draft and self.preview_html:
            draft.write({"rendered_html": Markup(self.preview_html)})

        return draft

    def _sync_html_to_draft(self, draft, html_str):
        """
        Save html_str to draft.rendered_html and sync each contract-section
        back to the corresponding draft article line.
        """
        import re as _re
        draft.write({"rendered_html": Markup(html_str)})
        section_contents = _re.findall(
            r'<div class="contract-section"[^>]*>(.*?)</div>\s*(?=<div class="contract-section"|$)',
            html_str,
            _re.DOTALL,
        )
        if section_contents:
            active_articles = draft.article_ids.filtered(
                lambda a: a.is_active and a.content
            ).sorted("sequence")
            for article, new_content in zip(active_articles, section_contents):
                cleaned = new_content.strip()
                if cleaned and cleaned != str(article.content or "").strip():
                    article.write({"content": Markup(cleaned)})
            _logger.info(
                "_sync_html_to_draft: synced %d sections to draft id=%s",
                len(section_contents), draft.id
            )

    def action_save_to_archive(self):
        self.ensure_one()
        draft = self._get_or_create_draft_archive()
        if draft and self.preview_html:
            self._sync_html_to_draft(draft, str(self.preview_html))
        
        return super().action_save_to_archive()



    def action_download_docx(self):
        """Save edited HTML to draft archive (with article sync), then redirect to DOCX download controller."""
        self.ensure_one()
        draft = self._get_or_create_draft_archive()
        if draft and self.preview_html:
            html_str = str(self.preview_html)
            self._sync_html_to_draft(draft, html_str)
            self.env.cr.flush()
            _logger.info(
                "action_download_docx: saved %d chars to draft archive id=%s for sale=%s",
                len(html_str), draft.id, self.sale_id.name
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'draft_docx_html_{self.sale_id.id}',
                html_str
            )
        if self.sale_id:
            self.sale_id.message_post(body=_("Contract edited and downloaded as DOCX."))
        return {
            'type': 'ir.actions.act_url',
            'url': f"/draft_archive/docx/download/{self.sale_id.id}",
            'target': 'new',
        }

    def action_print_pdf(self):
        """Save to draft archive (with article sync), then print PDF."""
        self.ensure_one()
        draft = self._get_or_create_draft_archive()
        if draft and self.preview_html:
            self._sync_html_to_draft(draft, str(self.preview_html))
        
        return super().action_print_pdf()
   

   
    def default_get(self, fields_list):
        """
        Override parent's default_get with priority:
        1. draft.contract.archive.rendered_html
        2. contract.archive.rendered_html
        3. Fresh render from template (parent's logic)
        """
        # Call parent's default_get which handles fresh render
        res = super().default_get(fields_list)
        
        sale_id = self.env.context.get("default_sale_id")
        if not sale_id:
            return res
        
        sale = self.env["property.sale"].browse(sale_id)
        
        # Validate contract template exists (from parent)
        if not sale.contract_section_template_id:
            raise UserError(
                ("A Contract Template must be selected before preview.")
            )
        
        # 1. Try draft.contract.archive - PRIORITY 1
        draft = (
            self.env["draft.contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], 
                limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sale_id", "=", sale.id), ("status", "!=", "void")], 
                limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sales_no", "=", sale.name), ("status", "!=", "void")], 
                limit=1
            )
        )
        
        if draft and draft.rendered_html:
            res["preview_html"] = Markup(draft.rendered_html)
            res["sale_id"] = sale_id
            return res
        
        # 2. Fall back to contract.archive.rendered_html - PRIORITY 2
        archive = (
            self.env["contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], 
                limit=1
            )
            or self.env["contract.archive"].search(
                [("sales_no", "=", sale.name), ("status", "!=", "void")], 
                limit=1
            )
        )
        
        if archive and archive.rendered_html:
            res["preview_html"] = Markup(archive.rendered_html)
            res["sale_id"] = sale_id
            return res
        
        # 3. Use parent's rendered_html if available - PRIORITY 3
        # Parent's default_get already handles fresh render
        # Just ensure sale_id is in response
        res["sale_id"] = sale_id
        
        return res














