from odoo import models


class InstallmentUpdateLog(models.Model):
    _inherit = "installment.update.log"

    def action_open_fix_wizard(self):
        """Open the standalone Fix Missed Installment wizard."""
        return {
            "type": "ir.actions.act_window",
            "name": "Fix Missed Installment",
            "res_model": "fix.missed.installment.wizard",
            "view_mode": "form",
            "target": "new",
        }
