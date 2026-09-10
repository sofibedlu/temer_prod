import logging
from odoo import models, _, api
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class PropertySaleDraftArchive(models.Model):
    _inherit = "property.sale"

    def action_confirm(self):
        """
        After the standard confirm (which creates contract.archive),
        also create a DraftContractArchive cloned from the new archive.
        """
        res = super().action_confirm()

        for sale in self:
            if not sale.contract_section_template_id:
                continue
            try:
                archive = (
                    self.env["contract.archive"].search(
                        [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
                    )
                    or self.env["contract.archive"].search(
                        [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
                    )
                )
                if not archive:
                    _logger.warning(
                        "DraftArchive: no contract.archive found for sale %s", sale.name
                    )
                    continue

                self.env["draft.contract.archive"].create_from_archive(archive.id)
               
            except Exception as e:
                _logger.error(
                    "DraftArchive: failed to create draft archive for sale %s: %s",
                    sale.name, str(e),
                )

        return res

    def action_print_contract(self):
        """
        Override: open the contract.preview.wizard pre-loaded with the
        draft.contract.archive HTML (if one exists), otherwise fall back
        to the standard re-render from the template.
        """
        self.ensure_one()

        if not self.contract_section_template_id:
            raise UserError(_("A Contract Template must be selected before you can print."))

        # Find the draft archive for this sale
        draft = (
            self.env["draft.contract.archive"].search(
                [("sale_id", "=", self.id), ("status", "!=", "void")],
                limit=1,
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sale_id", "=", self.id), ("status", "!=", "void")],
                limit=1,
            )
            or self.env["draft.contract.archive"].search(
                [("source_archive_id.sales_no", "=", self.name), ("status", "!=", "void")],
                limit=1,
            )
        )

        if draft and draft.rendered_html:
            wizard = self.env["contract.preview.wizard"].create({
                "sale_id":      self.id,
                "preview_html": Markup(draft.rendered_html),
            })
          
            return {
                "type": "ir.actions.act_window",
                "name": _("Contract Preview"),
                "res_model": "contract.preview.wizard",
                "view_mode": "form",
                "res_id": wizard.id,
                "target": "new",
            }

        # Fallback: standard behaviour (re-render from template)
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Preview"),
            "res_model": "contract.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_id": self.id,
            },
        }
