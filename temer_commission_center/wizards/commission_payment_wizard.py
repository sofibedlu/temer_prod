from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TemerCommissionPaymentWizard(models.TransientModel):
    _name = "temer.commission.payment.wizard"
    _description = "Commission Payment Wizard"

    sheet_line_id = fields.Many2one("temer.commission.sheet.line", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="sheet_line_id.currency_id", readonly=True)
    payment_date = fields.Date(default=fields.Date.context_today, required=True)

    amount = fields.Monetary(currency_field="currency_id", required=True)
    percentage = fields.Float(string="Percentage (%)", digits=(16, 6))

    note = fields.Char()
    remaining_balance = fields.Monetary(
        string="Remaining Balance",
        currency_field="currency_id",
        compute="_compute_remaining_balance",
        readonly=True,
        help="Remaining commission amount to be paid for this beneficiary."
    )

    @api.depends("sheet_line_id.balance_amount")
    def _compute_remaining_balance(self):
        for w in self:
            w.remaining_balance = w.sheet_line_id.balance_amount or 0.0

    @api.onchange("amount")
    def _onchange_amount(self):
        for w in self:
            total = w.sheet_line_id.total_commission_amount or 0.0
            if total > 0:
                w.percentage = (w.amount / total) * 100.0
            else:
                w.percentage = 0.0

    @api.onchange("percentage")
    def _onchange_percentage(self):
        for w in self:
            total = w.sheet_line_id.total_commission_amount or 0.0
            if total > 0:
                w.amount = (w.percentage / 100.0) * total
            else:
                w.amount = 0.0

    def action_confirm(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Amount must be greater than 0."))
        
        remaining_balance = self.sheet_line_id.balance_amount
        # ---------------
        # Optional: If 'pending' bills or payments are considered as already 'reserved' money, it can subtracted here.
        if self.amount > remaining_balance:
            raise ValidationError(_(
                "You cannot pay %(amount)s because it exceeds the remaining balance of %(balance)s.",
                amount=self.amount,
                balance=remaining_balance
            ))
        # ---------------

        payment = self.env["temer.commission.payment"].create({
            "sheet_line_id": self.sheet_line_id.id,
            "amount": self.amount,
            "note": self.note,
            "payment_date": self.payment_date,
            "approval_state": "prepared",
        })
        payment.action_prepare_payment()
        
        return {"type": "ir.actions.act_window_close"}