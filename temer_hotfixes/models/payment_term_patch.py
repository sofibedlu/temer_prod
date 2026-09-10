from odoo import api, models


class PropertyPaymentTerm(models.Model):
    _inherit = "property.payment.term"

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent creating "fixed" termsge)
        for vals in vals_list:
            if vals.get("payment_type") == "fixed":
                vals["payment_type"] = "percentage"
        return super().create(vals_list)

    def write(self, vals):
        # Prevent switching to "fixed" later
        if vals.get("payment_type") == "fixed":
            vals = dict(vals, payment_type="percentage")
        return super().write(vals)