from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class PropertySiteConstructionProgress(models.Model):
    _inherit = "property.site.construction.progress"

    date = fields.Date(string="Completed Date", readonly=False, tracking=True)

    def action_approve(self):
        """ Ensure the user has selected a date before approving. """
        for rec in self:
            if not rec.date:
                raise UserError(_("Please provide a 'Completed Date' before approving. This date will be used to shift the collection due dates."))
        return super().action_approve()

    def _process_completion(self):
        """ 
        OVERRIDE
        """
        Installment = self.env["collection.installment"]
        ShiftCfg = self.env["collection.progress.shift.config"]

        for rec in self:
            if not rec.site_id:
                raise UserError(_("Please set Site on the progress entry before completing."))

            term_line = getattr(rec, 'payment_term_line_id', False)
            if not term_line:
                raise UserError(_("Please select Payment Term Line (milestone/term) before completing."))

            # Security fallback
            if not rec.date:
                raise UserError(_("Completed Date is required."))

            cfg = ShiftCfg.search([("site_id", "=", rec.site_id.id), ("active", "=", True)], limit=1)
            enabled = True if not cfg else bool(cfg.enabled)
            shift_days = 30 if not cfg else (cfg.shift_days or 30)

            if not enabled:
                rec.state = "done"
                rec.message_post(body=_("100%% Reached. Due date shifting is disabled for site '%s'.") % rec.site_id.display_name)
                continue

            # domain = [
            #     ("collection_id.state", "=", "active"),
            #     ("collection_id.sale_id.payment_schedule_type", "=", "progress"),
            #     ("site_id", "=", rec.site_id.id),
            #     ("payment_term_line_id", "=", term_line.id),
            #     ("state", "!=", "paid"),
            # ]

            domain = [
                ("collection_id.state", "=", "active"),
                ("collection_id.sale_id.payment_schedule_type", "=", "progress"),
                ("site_id", "=", rec.site_id.id),
                ("state", "!=", "paid"),
                "|", 
                ("payment_term_line_id", "=", term_line.id),
                ("payment_term_line_id.name", "=", term_line.name),
            ]

            installments = Installment.sudo().search(domain)
            touched_collections = self.env["collection.order"]
            
            # Use the user's selected date as the absolute base reference
            base_reference_date = rec.date

            for inst in installments:
                new_due_date = base_reference_date + relativedelta(days=shift_days)
                
                inst.with_context(
                    due_date_update_source='progress',
                    progress_ref=f"Construction Progress ({rec.name})"
                ).write({
                    "due_date": new_due_date,
                    "due_date_set_by_progress": True,
                    "progress_entry_id": rec.id,
                    "progress_due_date_set_date": fields.Date.context_today(self), # Auditing field for when the button was clicked
                })
                touched_collections |= inst.collection_id

            rec.state = "done"
            rec.message_post(body=_("100%% Checked and Completed. Updated %s installment(s) using base date %s.") % (len(installments), base_reference_date))