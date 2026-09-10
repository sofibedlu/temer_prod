from datetime import timedelta
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TemerLead(models.Model):
    _inherit = "temer.lead"

    @api.model
    def make_expire_temer_lead_action(self, batch_size=1000):
        """Expire follow-up leads not updated in last 30 days."""
        _logger.info("==== Running make_expire_temer_lead_action ====")
        target_date = fields.Datetime.to_datetime(fields.Datetime.now()) - timedelta(days=30)
        target_date_str = fields.Datetime.to_string(target_date)

        lead_model = self.sudo()
        before_follow_up = lead_model.search_count([("state", "=", "follow_up")])
        before_expired = lead_model.search_count([("state", "=", "expired")])
        domain = [
            ("write_date", "<", target_date_str),
            ("state", "=", "follow_up"),
        ]
        leads = lead_model.with_context(skip_activity_report_update=True).search(domain, order="id ASC", limit=batch_size)
        _logger.info(
            "Temer lead expiration rule: state=follow_up and write_date<%s; candidates=%s (batch_size=%s).",
            target_date_str,
            len(leads),
            batch_size,
        )

        success_count = 0
        fail_count = 0
        for idx, lead in enumerate(leads, 1):
            try:
                # Direct expire write; avoid nested hooks that call cr.commit().
                lead._expire_leads()
                # Commit only after the lead is fully expired so count stays consistent.
                self.env.cr.commit()
                success_count += 1
                if idx % 50 == 0:
                    _logger.info("Temer lead expiration committed after %s leads.", idx)
            except Exception:
                fail_count += 1
                _logger.exception("Failed expiring Temer lead id=%s", lead.id)
                # Recover cursor for the next lead only; previous commits stay.
                self.env.cr.rollback()

        _logger.info(
            "==== Temer expiration batch complete: total=%s success=%s failed=%s ====",
            len(leads),
            success_count,
            fail_count,
        )
        after_follow_up = lead_model.search_count([("state", "=", "follow_up")])
        after_expired = lead_model.search_count([("state", "=", "expired")])
        _logger.info(
            "Temer state counts | follow_up: %s -> %s (delta=%s), expired: %s -> %s (delta=%s)",
            before_follow_up,
            after_follow_up,
            after_follow_up - before_follow_up,
            before_expired,
            after_expired,
            after_expired - before_expired,
        )

    def _expire_leads(self):
        """Expire leads and delete their phone numbers without calling lead.write()."""
        for lead in self:
            previous_state = lead.state
            if lead.phone_ids:
                lead.phone_ids.unlink()
                _logger.info("Deleted phone numbers for expired lead %s", lead.name)
            # Use direct SQL update to avoid overridden write() hooks in other modules
            # that perform explicit commits and break cron transaction consistency.
            self.env.cr.execute(
                f"""
                UPDATE "{self._table}"
                   SET state = %s,
                       prospect_date = NULL,
                       write_uid = %s,
                       write_date = NOW()
                 WHERE id = %s
                """,
                ("expired", self.env.uid, lead.id),
            )
            # This Odoo build does not expose invalidate_cache on recordsets.
            # Flush invalidation broadly so subsequent ORM reads see updated state.
            self.env.invalidate_all()

            # Keep stage history behavior expected by dashboards.
            if previous_state and previous_state != "expired":
                self.env["temer.lead.stage.history"].sudo().create({
                    "lead_id": lead.id,
                    "from_stage": previous_state,
                    "to_stage": "expired",
                    "transition_date": fields.Datetime.now(),
                })
