# -*- coding: utf-8 -*-
import logging
from odoo import models, _, api
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class PropertySaleDraftStatusAction(models.Model):
    _inherit = "property.sale"

    def _resolve_contract_html(self):
    
        draft = (
            self.env["draft.contract.archive"].search(
                [("sale_id", "=", self.id), ("status", "!=", "void")], limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sale_id", "=", self.id), ("status", "!=", "void")], limit=1
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sales_no", "=", self.name), ("status", "!=", "void")], limit=1
            )
        )

        if not draft:
            _logger.info("_resolve_contract_html: no draft found for sale=%s", self.name)
            return None, None

        draft_status = getattr(draft, 'draft_status', 'draft')
        
        _logger.info(
            "_resolve_contract_html_draft: sale=%s draft_id=%s draft_status=%s",
            self.name, draft.id, draft_status
        )

        if draft_status == 'saved':
            archive = (
                self.env["contract.archive"].search(
                    [("sale_id", "=", self.id), ("status", "!=", "void")], limit=1
                )
                or self.env["contract.archive"].search(
                    [("sales_no", "=", self.name), ("status", "!=", "void")], limit=1
                )
            )
            if archive and archive.rendered_html:
                _logger.info(
                    "_resolve_contract_html_saved: returning contract.archive id=%s (%d chars)",
                    archive.id, len(str(archive.rendered_html))
                )
                return archive.rendered_html, 'archive'
            _logger.warning(
                "_resolve_contract_html: draft_status=saved but contract.archive has no html, falling back to draft"
            )
            # fallback to draft if archive is empty
            if draft.rendered_html:
                return draft.rendered_html, 'draft_fallback'
            return None, None

        else:  # 'draft'
            if draft.rendered_html:
                _logger.info(
                    "_resolve_contract_html: returning draft.contract.archive id=%s (%d chars)",
                    draft.id, len(str(draft.rendered_html))
                )
                return draft.rendered_html, 'draft'
            return None, None

    def action_print_contract(self):
      
        self.ensure_one()

        if not self.contract_section_template_id:
            raise UserError(_("A Contract Template must be selected before you can print."))

        html, source = self._resolve_contract_html()

        if html:
            wizard = self.env["contract.preview.wizard"].create({
                "sale_id": self.id,
                "preview_html": Markup(str(html)),
            })
            _logger.info(
                "action_print_contract: wizard created from %s for sale=%s", source, self.name
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("Contract Preview"),
                "res_model": "contract.preview.wizard",
                "view_mode": "form",
                "res_id": wizard.id,
                "target": "new",
            }

      
        _logger.info("action_print_contract: no html, calling base template render for sale=%s", self.name)
  
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Preview"),
            "res_model": "contract.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sale_id": self.id},
        }
