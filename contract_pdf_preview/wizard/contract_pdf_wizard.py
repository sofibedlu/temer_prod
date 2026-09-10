from odoo import models, _
from markupsafe import Markup


class ContractPdfPreviewWizard(models.TransientModel):
    _inherit = "contract.preview.wizard"

    def _save_html_to_archive(self):
        """Persist edited preview_html back to the contract archive."""
        sale = self.sale_id
        archive = (
            self.env["contract.archive"].search(
                [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
            )
            or self.env["contract.archive"].search(
                [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
            )
        )
        if archive and self.preview_html:
            archive.write({"rendered_html": self.preview_html})
        return archive

    def action_print_pdf(self):
        """
        Override: save edits first, then render via the contract_managment
        QWeb report (wkhtmltopdf) — same as the base wizard but with
        the latest edited HTML.
        """
        self.ensure_one()
        

        sale = self.sale_id

        def get_full_name():
            if not sale.contract_id:
                return "—"
            names = []
            for person in sale.contract_id:
                fname = getattr(person, "first_name", "") or ""
                mname = getattr(person, "father_name", "") or ""
                lname = getattr(person, "gfather_name", "") or ""
                full = f"{fname} {mname} {lname}".strip()
                if full:
                    names.append(full)
            return ", ".join(names) if names else "—"

        datas = {
            "full_content": Markup(self.preview_html) if self.preview_html else Markup(""),
            "stamp": "",
            "customer_name": get_full_name(),
        }

        report = self.env.ref("contract_managment.action_report_contract")
        return report.report_action(sale, data=datas)

    def action_preview_pdf(self):
        """Open the HTML preview in a new browser tab."""
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_url",
            "url": f"/contract/pdf/preview/{self.sale_id.id}",
            "target": "new",
        }

    def action_download_pdf(self):
        """Download PDF via Odoo's report engine (wkhtmltopdf)."""
        self.ensure_one()
        
        report = self.env.ref("contract_managment.action_report_contract")
        sale = self.sale_id
        datas = {
            "full_content": Markup(self.preview_html) if self.preview_html else Markup(""),
            "stamp": "",
            "customer_name": "",
        }
        return report.report_action(sale, data=datas)

    def action_download_docx(self):
        """Open DOCX download in a new tab."""
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_url",
            "url": f"/contract/docx/download/{self.sale_id.id}",
            "target": "new",
        }
