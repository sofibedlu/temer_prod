from odoo import fields, models, _


class TemerCommissionCloseWizard(models.TransientModel):
    _name = "temer.commission.cancel.wizard"
    _description = "Commission Cancel Wizard"

    sheet_id = fields.Many2one("temer.commission.sheet", required=True, readonly=True)
    reason = fields.Text(string="Cancel Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.sheet_id.state = "cancelled"
        self.sheet_id.message_post(
            body=_("Commission Sheet Cancelled. Reason: %s") % self.reason,
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.act_window_close"}