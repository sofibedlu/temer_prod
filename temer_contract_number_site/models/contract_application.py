from odoo import api, models, _
from odoo.exceptions import ValidationError


class ContractApplication(models.Model):
    _inherit = "contract.application"

    @api.constrains("name")
    def _check_contract_number_unique(self):
        if self.env.context.get("skip_contract_unique_check"):
            return
        
        for rec in self:
            name = (rec.name or "").strip()
            if not name or name in ("Draft Contract", "New"):
                continue

            dup = self.sudo().search(
                [("name", "=", name), ("id", "!=", rec.id)],
                limit=1,
            )
            if dup:
                raise ValidationError(
                    _("Contract Number must be unique. '%s' is already used.") % name
                )