from odoo import api, fields, models


class TemerCommissionPolicy(models.Model):
    _name = "temer.commission.policy"
    _description = "Commission Policy"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    line_ids = fields.One2many("temer.commission.policy.line", "policy_id", string="Rules")
    note = fields.Text(string="Notes")


class TemerCommissionPolicyLine(models.Model):
    _name = "temer.commission.policy.line"
    _description = "Commission Policy Rule"
    _order = "sequence, id"

    policy_id = fields.Many2one("temer.commission.policy", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)

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

    percentage = fields.Float(string="Commission %", digits=(16, 6), required=True)
    active = fields.Boolean(default=True)