import re
from odoo import api, models
from markupsafe import Markup


class ContractPdfReport(models.AbstractModel):
    """
    Report parser for contract_pdf_preview.contract_pdf_report.
    Called by Odoo's report engine when rendering
    /report/pdf/contract_pdf_preview.contract_pdf_report/<wizard_id>
    """
    _name = "report.contract_pdf_preview.contract_pdf_report"
    _description = "Contract PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        # docids contains the contract.preview.wizard id(s)
        wizard = self.env["contract.preview.wizard"].browse(docids)
        wizard.ensure_one()

        sale = wizard.sale_id
        archive = (
            self.env["contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["contract.archive"].search(
                [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
            )
        )

        if archive and wizard.preview_html:
            # Use the wizard's edited HTML
            raw = str(wizard.preview_html)
        elif archive:
            raw = str(
                archive.rendered_html
                if archive.rendered_html
                else sale.contract_section_template_id.render_full_contract(
                    sale.contract_id, archive
                )
            )
        else:
            raw = ""

        # Strip sig-footer divs
        content = re.sub(
            r'<div[^>]*class=["\'][^"\']*sig-footer[^"\']*["\'][^>]*>.*?</div>',
            "", raw, flags=re.DOTALL
        )
        # Strip any company header box stored in the HTML
        content = re.sub(
            r'<div[^>]*class=["\'][^"\']*(?:header-box|header-main|header-mini|cp-header-box)[^"\']*["\'][^>]*>.*?</div>',
            "", content, flags=re.DOTALL
        )

        return {
            "doc_ids":    docids,
            "doc_model":  "contract.preview.wizard",
            "docs":       wizard,
            "sale":       sale,
            "content":    Markup(content),
        }
