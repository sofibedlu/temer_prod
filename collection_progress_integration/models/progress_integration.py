from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

try:
    from ethiopian_date import EthiopianDateConverter
except Exception:
    EthiopianDateConverter = None


class PropertySiteConstructionProgress(models.Model):
    _inherit = "property.site.construction.progress"
    _order = 'create_date desc, id desc'

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("checked", "Checked"),
            ("done", "Completed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
    )
    date = fields.Date(string="Completed Date", readonly=True)
    progress_percentage = fields.Float(string="Progress (%)", default=0.0, tracking=True)

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("You cannot delete a progress record that is already in 'Completed' state."))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.progress_percentage > 0.0:
                rec.message_post(
                    body=_("Initial Progress set to: %s%%") % rec.progress_percentage,
                    subtype_xmlid="mail.mt_note"
                )
            # if rec.progress_percentage >= 100.0 and rec.state != 'done':
            #     rec._process_completion()
        return records

    # def write(self, vals):
    #     res = super().write(vals)
    #     if 'progress_percentage' in vals:
    #         for rec in self:
    #             if rec.progress_percentage >= 100.0 and rec.state != 'done':
    #                 rec._process_completion()
    #     return res

    def action_check(self):
        for rec in self:
            if getattr(rec, 'progress_percentage', 0) < 100:
                raise UserError(_("Progress must be 100% to check."))
            rec.state = 'checked'

    def action_approve(self):
        for rec in self:
            if getattr(rec, 'progress_percentage', 0) < 100:
                raise UserError(_("Progress must be 100% to approve."))
            rec._process_completion()

    def _process_completion(self):
        Installment = self.env["collection.installment"]
        ShiftCfg = self.env["collection.progress.shift.config"]

        for rec in self:
            if not rec.site_id:
                raise UserError(_("Please set Site on the progress entry before completing."))

            term_line = getattr(rec, 'payment_term_line_id', False)
            if not term_line:
                raise UserError(_("Please select Payment Term Line (milestone/term) before completing."))

            rec.date = fields.Date.context_today(self)
            cfg = ShiftCfg.search([("site_id", "=", rec.site_id.id), ("active", "=", True)], limit=1)
            enabled = True if not cfg else bool(cfg.enabled)
            shift_days = 30 if not cfg else (cfg.shift_days or 30)

            if not enabled:
                rec.state = "done"
                rec.message_post(body=_("100%% Reached. Due date shifting is disabled for site '%s'.") % rec.site_id.display_name)
                continue

            domain = [
                ("collection_id.state", "=", "active"),
                ("collection_id.sale_id.payment_schedule_type", "=", "progress"),
                ("site_id", "=", rec.site_id.id),
                ("payment_term_line_id", "=", term_line.id),
                ("state", "!=", "paid"),
            ]

            installments = Installment.sudo().search(domain)
            touched_collections = self.env["collection.order"]
            today = fields.Date.context_today(self)

            for inst in installments:
                base_date = inst.due_date or today
                new_due_date = base_date + relativedelta(days=shift_days)
                inst.with_context(
                    due_date_update_source='progress',
                    progress_ref=f"Construction Progress ({rec.name})"
                ).write({
                    "due_date": new_due_date,
                    "due_date_set_by_progress": True,
                    "progress_entry_id": rec.id,
                    "progress_due_date_set_date": today,
                })
                touched_collections |= inst.collection_id

            rec.state = "done"
            rec.message_post(body=_("100%% Checked and Completed. Updated %s installment(s).") % len(installments))


class CollectionInstallment(models.Model):
    _inherit = "collection.installment"

    due_date_set_by_progress = fields.Boolean(
        string="Due Date Set by Progress",
        default=False,
        copy=False,
        help="Checked when due_date was set/shifted by a construction progress completion.",
    )
    progress_entry_id = fields.Many2one(
        "property.site.construction.progress",
        string="Progress Entry",
        copy=False,
        readonly=True,
    )
    progress_due_date_set_date = fields.Date(
        string="Progress Confirmed Date",
        copy=False,
        readonly=True,
    )
    due_date_ethiopian = fields.Char(
        string="Due Date (Ethiopian)",
        compute="_compute_due_date_ethiopian",
        store=True,
        readonly=True,
        help="Ethiopian calendar equivalent of Due Date.",
    )

    @api.depends("due_date")
    def _compute_due_date_ethiopian(self):
        for rec in self:
            rec.due_date_ethiopian = rec._to_ethiopian_date_str(rec.due_date)

    @api.onchange("due_date")
    def _onchange_due_date_sync_ethiopian(self):
        for rec in self:
            rec.due_date_ethiopian = rec._to_ethiopian_date_str(rec.due_date)

    def _to_ethiopian_date_str(self, date_value):
        """Convert a Gregorian date (fields.Date) to DD/MM/YYYY Ethiopian string."""
        if not date_value or not EthiopianDateConverter:
            return ""
        try:
            eth_year, eth_month, eth_day = EthiopianDateConverter.to_ethiopian(
            date_value.year, date_value.month, date_value.day
            )
            return f"{eth_day:02d}/{eth_month:02d}/{eth_year}"
        except ValueError:
            if date_value.month == 9 and 5 <= date_value.day <= 11:
                eth_year = date_value.year - 8
                pagume_day = date_value.day - 5
                return f"{pagume_day:02d}/13/{eth_year}"
            return ""