from odoo import models


class PropertySale(models.Model):
    _inherit = "property.sale"

    def action_confirm(self):
        res = super().action_confirm()

        Sheet = self.env["temer.commission.sheet"]
        for sale in self:
            sheet = Sheet.search([("sale_id", "=", sale.id)], limit=1)
            if not sheet:
                sheet = Sheet.create({
                    "sale_id": sale.id,
                    "sale_amount": sale.sale_price,
                })
                # Generate beneficiaries
                sheet.action_generate_lines_from_sale()
        return res