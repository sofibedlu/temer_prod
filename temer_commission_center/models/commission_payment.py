from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TemerCommissionPayment(models.Model):
    _name = "temer.commission.payment"
    _description = "Commission Payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    sheet_line_id = fields.Many2one("temer.commission.sheet.line", required=True, ondelete="cascade")
    sheet_id = fields.Many2one(related="sheet_line_id.sheet_id", store=True, readonly=True)

    company_id = fields.Many2one(related="sheet_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="sheet_id.currency_id", store=True, readonly=True)

    partner_id = fields.Many2one(related="sheet_line_id.partner_id", store=True, readonly=True)
    payment_date = fields.Date(string="Payment Date", default=fields.Date.context_today, tracking=True)

    amount = fields.Monetary(currency_field="currency_id", required=True)
    note = fields.Char()

    #-- backward compatibility fields --#
    bill_id = fields.Many2one(
        "account.move",
        string="Vendor Bill",
        domain=[("move_type", "=", "in_invoice")],
    )

    bill_state = fields.Selection(
        related="bill_id.state",
        string="Bill Status",
        readonly=True,
    )
    bill_payment_state = fields.Selection(
        related="bill_id.payment_state",
        string="Bill Payment State",
        readonly=True,
    )
    #-- backward compatibility fields --#

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("prepared", "Prepared"),
            ("checked", "Checked"),
            ("approved", "Approved"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )

    payment_id = fields.Many2one(
        "account.payment",
        string="Vendor Payment",
        readonly=True,
        copy=False,
        tracking=True,
    )
    payment_state = fields.Selection(
        related="payment_id.state",
        string="Payment Status",
        readonly=True,
    )

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_status",
        store=True,
        tracking=True,
    )

    @api.depends(
        "approval_state",
        "payment_id",
        "payment_id.state",
        "bill_id",
        "bill_id.state",
        "bill_id.payment_state",
    )
    def _compute_status(self):
        for rec in self:
            # For status from vendor payment
            if rec.approval_state == "cancelled":
                rec.status = "cancelled"
            elif rec.payment_id and rec.payment_id.state == "posted":
                rec.status = "paid"
            # Backward compatibility: old bill-based records
            elif rec.bill_id and rec.bill_id.state == "posted" and rec.bill_id.payment_state == "paid":
                rec.status = "paid"
            else:
                rec.status = "pending"
    
    def action_prepare_payment(self):
        self.ensure_one()
        if self.approval_state in ("prepared", "approved"):
            return True
        if self.approval_state == "cancelled":
            raise UserError(_("Cancelled payments cannot be prepared."))
        self.approval_state = "prepared"
        return True
    
    def action_check_payment(self):
        """Mark a prepared commission payment as checked."""
        self.ensure_one()
        if self.approval_state != "prepared":
            raise UserError(_("Only Prepared payments can be checked."))
        self.approval_state = "checked"
        return True
    
    def action_approve_prepared_payment(self):
        """Approve -> create a DRAFT vendor payment (account.payment)."""
        self.ensure_one()
        if self.approval_state != "checked":
            raise UserError(_("Only Checked payments can be approved."))
        if self.payment_id:
            self.approval_state = "approved"
            return True

        company = self.company_id

        journal = self.env["account.journal"].search(
            [("type", "in", ("bank", "cash")), ("company_id", "=", company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_("Please configure a Bank/Cash Journal for company %s.") % company.display_name)

        payment_vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "date": self.payment_date or fields.Date.context_today(self),
            "journal_id": journal.id,
            "ref": self.sheet_id.name or _("Commission Sheet"),
        }

        if "payment_method_line_id" in self.env["account.payment"]._fields:
            method_line = journal.outbound_payment_method_line_ids[:1]
            if not method_line:
                raise UserError(_("No outbound payment method is configured on journal %s.") % journal.display_name)
            payment_vals["payment_method_line_id"] = method_line.id

        pay = self.env["account.payment"].create(payment_vals)
        self.payment_id = pay.id
        self.approval_state = "approved"
        return True

    def action_open_vendor_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_("No vendor payment created yet."))
        return {
            "name": _("Vendor Payment"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "form",
            "res_id": self.payment_id.id,
            "target": "current",
        }
    
    #-- backward compatibility methods --#
    def action_open_bill(self):
        self.ensure_one()
        if not self.bill_id:
            raise UserError(_("No vendor bill created yet."))
        return {
            "name": _("Vendor Bill"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.bill_id.id,
            "target": "current",
        }

    def action_create_draft_bill(self):
        self.ensure_one()
        if self.bill_id:
            raise UserError(_("A vendor bill is already linked to this commission payment."))

        company = self.company_id
        journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_("Please configure a Purchase Journal for company %s.") % company.display_name)

        expense_account = self.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not expense_account:
            raise UserError(_("Please configure an Expense account for company %s.") % company.display_name)

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": self.sheet_id.name or _("Commission Sheet"),
            "company_id": company.id,
            "journal_id": journal.id,
            "commission_payment_id": self.id,
            "invoice_line_ids": [(0, 0, {
                "name": _("Commission payment for %s") % (self.sheet_id.sale_id.name or self.sheet_id.name),
                "quantity": 1,
                "price_unit": self.amount,
                "account_id": expense_account.id,
            })],
        })
        self.bill_id = bill.id
        return True
    #-- backward compatibility methods --#