from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TemerCommissionSheet(models.Model):
    _name = "temer.commission.sheet"
    _description = "Commission Sheet"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="New", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    sale_id = fields.Many2one("property.sale", string="Property Sale", tracking=True)

    policy_id = fields.Many2one("temer.commission.policy", string="Commission Policy", tracking=True)

    sale_amount = fields.Monetary(string="Sale Amount", currency_field="currency_id", tracking=True)

    collection_order_id = fields.Many2one(
        "collection.order",
        string="Collection Order",
        related="sale_id.collection_order_id",
        store=True,
        readonly=True,
    )

    collected_amount = fields.Monetary(
        string="Collected Amount",
        currency_field="currency_id",
        related="collection_order_id.amount_collected",
        store=True,
        readonly=True,
    )

    collected_percentage = fields.Float(
        string="Collected %",
        compute="_compute_collected_percentage",
        store=False,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        compute="_compute_state",
        store=True,
        tracking=True,
    )

    line_ids = fields.One2many("temer.commission.sheet.line", "sheet_id", string="Beneficiaries")

    
    def _get_beneficiary_data(self, sale):
        """
        Helper to extract beneficiary data from a sale's reservation.
        """
        reservation = sale.reservation_id
        if not reservation:
            return []

        # Map user_id -> {percentage, amount}
        commission_data = {
            line.user_id.id: {'percentage': line.percentage, 'amount': line.amount}
            for line in sale.commission_detail_ids
            if line.user_id
        }

        def _as_user(rec):
            if not rec:
                return self.env["res.users"]
            if getattr(rec, "_name", "") == "res.users":
                return rec
            if hasattr(rec, "name") and rec.name and getattr(rec.name, "_name", "") == "res.users":
                return rec.name
            if hasattr(rec, "manager_id") and rec.manager_id and getattr(rec.manager_id, "_name", "") == "res.users":
                return rec.manager_id
            return self.env["res.users"]

        salesperson_users = reservation.salesperson_ids
        supervisor_user = _as_user(getattr(reservation, "supervisor_id", False))
        sales_manager_user = _as_user(getattr(reservation, "team_id", False))
        wing_manager_user = _as_user(getattr(reservation, "wing_id", False))

        role_user_pairs = []
        for sp in salesperson_users:
            role_user_pairs.append(("salesperson", sp))
        
        role_user_pairs.append(("supervisor", supervisor_user))
        role_user_pairs.append(("sales_manager", sales_manager_user))
        role_user_pairs.append(("wing_manager", wing_manager_user))

        seen_partner_ids = set()
        results = []
        for role, user in role_user_pairs:
            if not user or not user.id or not user.partner_id:
                continue
            if user.partner_id.id in seen_partner_ids:
                continue
            seen_partner_ids.add(user.partner_id.id)
            vals = commission_data.get(user.id, {'percentage': 0.0, 'amount': 0.0})

            results.append({
                "partner_id": user.partner_id.id,
                "role": role,
                "percentage": vals['percentage'],
                "total_commission_amount": vals['amount'],
            })
        return results
    
    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        for rec in self:
            if rec.sale_id:
                rec.sale_amount = rec.sale_id.sale_price or 0.0
                rec.collection_order_id = rec.sale_id.collection_order_id.id if rec.sale_id.collection_order_id else False

                if rec.sale_id.reservation_id:
                    if not rec.sale_id.commission_detail_ids:
                        try:
                            rec.sale_id.calculate_commission()
                        except Exception:
                            pass
                    
                    data = rec._get_beneficiary_data(rec.sale_id)
                    rec.line_ids = [(5, 0, 0)] + [(0, 0, d) for d in data]
            else:
                rec.sale_amount = 0.0
                rec.collection_order_id = False
                rec.line_ids = [(5, 0, 0)]

    @api.depends("sale_amount", "collected_amount")
    def _compute_collected_percentage(self):
        for rec in self:
            sale_amount = rec.sale_amount or 0.0
            rec.collected_percentage = (rec.collected_amount / sale_amount * 100.0) if sale_amount else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("temer.commission.sheet") or "New"
        return super().create(vals_list)

    @api.depends("line_ids.state")
    def _compute_state(self):
        for sheet in self:
            if sheet.line_ids and all(line.state == "paid" for line in sheet.line_ids):
                sheet.state = "closed"

    def action_generate_lines_from_sale(self):
        """
        Generate beneficiaries from property.sale.reservation_id and fetch percentages
        from the sale's calculated commission details.
        """
        for sheet in self:
            if not sheet.sale_id:
                raise UserError(_("Please set Property Sale first."))

            reservation = sheet.sale_id.reservation_id
            if not reservation:
                raise UserError(_("This sale has no Reservation linked. Please set reservation_id on the sale."))

            # Trigger calculation on the sale to get default percentages/amounts
            # clear existing DRAFT details first to avoid duplicates
            sheet.sale_id.commission_detail_ids.filtered(lambda c: c.state == 'draft').unlink()
            sheet.sale_id.calculate_commission()

            # Map user_id -> {percentage, amount} from the calculated details
            commission_data = {
                line.user_id.id: {'percentage': line.percentage, 'amount': line.amount}
                for line in sheet.sale_id.commission_detail_ids
                if line.user_id
            }

            def _as_user(rec):
                if not rec:
                    return self.env["res.users"]
                if getattr(rec, "_name", "") == "res.users":
                    return rec
                if hasattr(rec, "name") and rec.name and getattr(rec.name, "_name", "") == "res.users":
                    return rec.name
                if hasattr(rec, "manager_id") and rec.manager_id and getattr(rec.manager_id, "_name", "") == "res.users":
                    return rec.manager_id
                return self.env["res.users"]

            salesperson_users = reservation.salesperson_ids
            supervisor_user = _as_user(getattr(reservation, "supervisor_id", False))
            sales_manager_user = _as_user(getattr(reservation, "team_id", False))
            wing_manager_user = _as_user(getattr(reservation, "wing_id", False))

            role_user_pairs = []
            # for multiple salespersons
            for sp in salesperson_users:
                role_user_pairs.append(("salesperson", sp))
            
            role_user_pairs.append(("supervisor", supervisor_user))
            role_user_pairs.append(("sales_manager", sales_manager_user))
            role_user_pairs.append(("wing_manager", wing_manager_user))

            # Generate Lines
            sheet.line_ids.unlink()
            seen_partner_ids = set()
            lines = []
            for role, user in role_user_pairs:
                if not user or not user.id or not user.partner_id:
                    continue
                if user.partner_id.id in seen_partner_ids:
                    continue
                seen_partner_ids.add(user.partner_id.id)
                vals = commission_data.get(user.id, {'percentage': 0.0, 'amount': 0.0})

                lines.append((0, 0, {
                    "partner_id": user.partner_id.id,
                    "role": role,
                    "percentage": vals['percentage'],
                    "total_commission_amount": vals['amount'],
                }))

            sheet.write({"line_ids": lines})
    
    def action_confirm(self):
        self.ensure_one()
        if self.state == "draft":
            self.state = "confirmed"

    def action_cancel_with_reason(self):
        self.ensure_one()
        return {
            "name": "Cancel Commission Sheet",
            "type": "ir.actions.act_window",
            "res_model": "temer.commission.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sheet_id": self.id},
        }
    
    def action_calculate_commission(self):
        """
        Standalone commission calculation
        """
        self.ensure_one()
        if not self.sale_id:
            raise UserError(_("Please set Property Sale first."))
        if not self.line_ids:
            raise UserError(_("Please add beneficiaries first."))

        if not self.sale_amount:
            self.sale_amount = self.sale_id.sale_price

        if not self.sale_amount:
            raise UserError(_("Sale Amount is missing. Please set Sale Amount on the Commission Sheet."))
        
        # If a policy is selected
        if self.policy_id:
            policy_map = {line.role: line.percentage for line in self.policy_id.line_ids}
            for line in self.line_ids:
                pct = policy_map.get(line.role, line.percentage or 0.0)
                amount = (self.sale_amount * pct / 100.0) if pct else 0.0
                line.write({
                    "percentage": pct,
                    "total_commission_amount": amount,
                })
            return

        role_to_hierarchy_type = {
            "salesperson": "sales_person",
            "supervisor": "supervisor",
            "sales_manager": "sales_manager",
            "wing_manager": "wing_manager",
        }

        CommissionConfig = self.env["commission.configuration"]

        for line in self.line_ids:
            pct = line.percentage or 0.0

            # If user didn’t set percentage manually, pull default from config
            if pct <= 0.0 and line.role in role_to_hierarchy_type:
                cfg = CommissionConfig.search(
                    [("hierarchy_type", "=", role_to_hierarchy_type[line.role])],
                    limit=1,
                )
                if cfg and hasattr(cfg, "percentage"):
                    pct = cfg.percentage or 0.0

            amount = (self.sale_amount * pct / 100.0) if pct else 0.0

            line.write({
                "percentage": pct,
                "total_commission_amount": amount,
            })


class TemerCommissionSheetLine(models.Model):
    _name = "temer.commission.sheet.line"
    _description = "Commission Sheet Line"
    _order = "id asc"

    sheet_id = fields.Many2one("temer.commission.sheet", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="sheet_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="sheet_id.currency_id", store=True, readonly=True)

    partner_id = fields.Many2one("res.partner", string="Beneficiary", required=True)
    role = fields.Selection(
        [
            ("salesperson", "Salesperson"),
            ("supervisor", "Supervisor"),
            ("sales_manager", "Sales Manager"),
            ("wing_manager", "Wing Manager"),
            ("other", "Other"),
        ],
        required=True,
        default="salesperson",
    )

    percentage = fields.Float(string="Commission %", digits=(16, 6))
    total_commission_amount = fields.Monetary(string="Total Commission", currency_field="currency_id")

    payment_ids = fields.One2many("temer.commission.payment", "sheet_line_id", string="Payments")

    paid_amount = fields.Monetary(
        string="Paid Amount",
        currency_field="currency_id",
        compute="_compute_paid_amount",
        store=True,
    )
    balance_amount = fields.Monetary(
        string="Remaining Balance",
        currency_field="currency_id",
        compute="_compute_balance_amount",
        store=True,
    )
    state = fields.Selection(
        [
            ("unpaid", "Unpaid"),
            ("partial", "Partial"),
            ("paid", "Paid"),
        ],
        compute="_compute_state",
        store=True,
        tracking=True,
    )
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("partner_id", "role")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.partner_id.name} ({rec.role})" if rec.partner_id else rec.role

    @api.depends("payment_ids.amount", "payment_ids.status")
    def _compute_paid_amount(self):
        for line in self:
            paid_payments = line.payment_ids.filtered(lambda p: p.status == "paid")
            line.paid_amount = sum(paid_payments.mapped("amount") or [0.0])

    @api.depends("total_commission_amount", "paid_amount")
    def _compute_balance_amount(self):
        for line in self:
            line.balance_amount = (line.total_commission_amount or 0.0) - (line.paid_amount or 0.0)

    @api.depends("total_commission_amount", "paid_amount")
    def _compute_state(self):
        for line in self:
            if (line.paid_amount or 0.0) <= 0.0:
                line.state = "unpaid"
            elif (line.total_commission_amount or 0.0) > (line.paid_amount or 0.0):
                line.state = "partial"
            else:
                line.state = "paid"

    def action_open_payment_wizard(self):
        self.ensure_one()
        return {
            "name": "Register Commission Payment",
            "type": "ir.actions.act_window",
            "res_model": "temer.commission.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sheet_line_id": self.id,
                "default_amount": self.balance_amount if self.balance_amount > 0 else 0.0,
            },
        }