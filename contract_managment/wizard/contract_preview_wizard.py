from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup


class ContractPreviewWizard(models.TransientModel):
    _name = "contract.preview.wizard"
    _description = "Contract Preview & Editor"

    sale_id = fields.Many2one("property.sale", string="Sale", required=True)
    preview_html = fields.Html(string="Contract Content", sanitize=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_id = self.env.context.get("default_sale_id")
        if not sale_id:
            return res

        sale = self.env["property.sale"].browse(sale_id)
        if not sale.contract_section_template_id:
            raise UserError(_("A Contract Template must be selected before preview."))

        archive = (
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
        if not archive:
            raise UserError(_("No Contract Archive found. Please confirm the sale first."))

        raw_html = sale.contract_section_template_id.render_full_contract(
            sale.contract_id, archive
        )
        res["preview_html"] = Markup(raw_html) if raw_html else Markup("")
        res["sale_id"] = sale_id
        return res

    def action_print_pdf(self):
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
