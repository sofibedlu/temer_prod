# -*- coding: utf-8 -*-
import logging
from odoo import models
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class PropertySaleArchiveReset(models.Model):
    _inherit = "property.sale"

    def action_confirm(self):
        """
        Before confirming:
          1. Hard-delete any existing contract.archive for this sale
          2. Hard-delete any existing draft.contract.archive for this sale
          3. Post a chatter message summarising what was reset
        Then call super() which recreates both fresh.
        """
        for sale in self:
            if not sale.contract_section_template_id:
                continue

            archive_count = 0
            draft_count   = 0

            # ── 1. Hard-delete existing contract.archive ──
            archives = self.env["contract.archive"].sudo().search([
                "|",
                ("sale_id", "=", sale.id),
                ("sales_no", "=", sale.name),
            ])
            if archives:
                archive_count = len(archives)
                _logger.info(
                    "contract_archive_reset: deleting %d contract.archive(s) for sale=%s",
                    archive_count, sale.name,
                )
                archives.sudo().unlink()

            # ── 2. Hard-delete existing draft.contract.archive ──
            drafts = self.env["draft.contract.archive"].sudo().search([
                "|", "|",
                ("sale_id", "=", sale.id),
                ("source_archive_id.sale_id", "=", sale.id),
                ("source_archive_id.sales_no", "=", sale.name),
            ])
            if drafts:
                draft_count = len(drafts)
                _logger.info(
                    "contract_archive_reset: deleting %d draft.contract.archive(s) for sale=%s",
                    draft_count, sale.name,
                )
                drafts.sudo().unlink()

            # ── 3. Chatter message ──
            if archive_count or draft_count:
                sale.message_post(body=Markup(
                 
                    "Deleted  contract archive and  draft archive. "
                    
                ))
            else:
                sale.message_post(body=Markup(
                    "New contract archive and draft archive will be created."
                ))
        return super().action_confirm()
