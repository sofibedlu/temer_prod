# -*- coding: utf-8 -*-
"""
Single model for existing-customer SMS across all 4 CRMs (Reception, Website, Call Center, Affiliate).
All logic for "existing customer" message sending lives here; no use of crm_custom_menu for sending.
Sends 1 SMS if salesperson == supervisor, 2 SMS otherwise (salesperson + supervisor).
SMS can be sent in background so create/save returns fast (no waiting for gateway).
"""

import logging
import threading
import time

from odoo import _, api, models

_logger = logging.getLogger(__name__)

# Deduplication: skip sending if we already sent for (model_name, res_id) in the last 60 seconds
_sms_sent_recently = {}
_SMS_COOLDOWN_SEC = 60


class WingExistingCustomerSms(models.TransientModel):
    _name = "wing.existing.customer.sms"
    _description = "Wing: send SMS to existing salesperson/supervisor (1 or 2 messages)"
    _inherit = ["wing.sales.team.sms.mixin"]

    def send_for_record(self, record, source):
        """
        Send SMS for existing customer: get salesperson, supervisor, customer info from record;
        send 1 or 2 messages (same rule as Reception). No crm_custom_menu logic.

        :param record: crm.reception, crm.website, crm.callcenter, or crm.affilater
        :param source: str e.g. "Walk In", "Website", "Call Center (6033)", "Referral"
        :return: (success: bool, err_msg: str|None)
        """
        self.ensure_one()
        salesperson = getattr(record, "existing_salesperson_id", None) and record.existing_salesperson_id
        # Fallback: if we only have existing_temer_lead_id, use that lead's salesperson.
        # NOTE: we only trust lead.user_id if it is NOT the same as the user who created
        # the current reception/website record — that would mean the creator leaked into
        # the lead's user_id (the bug we fixed in crm_reception_inherit.py).
        if not salesperson and getattr(record, "existing_temer_lead_id", None):
            lead = record.existing_temer_lead_id
            lead_user = getattr(lead, "user_id", None)
            # Only use lead.user_id if it differs from the record's create_uid,
            # so we never accidentally send to the reception user who registered the lead.
            record_creator_id = getattr(record, "create_uid", None) and record.create_uid.id
            if lead_user and lead_user.id != record_creator_id:
                salesperson = lead_user
        if not salesperson:
            return False, _("No existing salesperson found for this phone number.")
        supervisor = getattr(record, "existing_supervisor_id", None) and record.existing_supervisor_id
        if not supervisor and hasattr(record, "_get_supervisor_for_salesperson"):
            supervisor = record._get_supervisor_for_salesperson(salesperson)
        customer_name = (getattr(record, "customer_name", None) or "").strip() or "Customer"
        customer_phone = ""
        if hasattr(record, "_get_customer_phone_from_record"):
            customer_phone = (record._get_customer_phone_from_record() or "").strip()
        else:
            customer_phone = (getattr(record, "phone_no", None) or getattr(record, "new_phone", None) or "").strip()
            if not customer_phone and getattr(record, "full_phone", None) and record.full_phone:
                customer_phone = (record.full_phone[0].name or "").strip()

        # Ensure the record carries a clear duplicate message (including no-phone cases)
        msg = self._wing_duplicate_message_for_salesperson(salesperson)
        if "phone_number_message" in record._fields:
            try:
                record.sudo().write({
                    "phone_number_message": msg,
                    "wing_duplicate_popup_pending": True,
                    # Keep draft if salesperson has no phone so user can fix.
                    "state_crm": "draft" if not self._wing_user_has_phone(salesperson) else record.state_crm,
                })
            except Exception:
                pass

        # If salesperson is missing phone, do not attempt to send.
        if not self._wing_user_has_phone(salesperson):
            _logger.info(
                "Wing existing customer SMS: skipping send because salesperson %s (id=%s) has no phone.",
                getattr(salesperson, "name", "<unknown>"),
                getattr(salesperson, "id", "<none>"),
            )
            return False, msg

        # Log what phone number we are sending to (helpful for debugging).
        sales_mobile = (
            getattr(salesperson.partner_id, "mobile", None)
            or getattr(salesperson.partner_id, "phone", None)
            or getattr(salesperson, "mobile", None)
            or getattr(salesperson, "phone", None)
        )
        _logger.info(
            "Wing existing customer SMS: sending to salesperson %s (id=%s) phone=%s for record %s(%s).",
            getattr(salesperson, "name", "<unknown>"),
            getattr(salesperson, "id", "<none>"),
            sales_mobile,
            record._name,
            record.id,
        )

        sms_source = (source or "").strip() or "Walk In"
        _logger.info(
            "Wing existing customer SMS: sending to salesperson %s (id=%s) via %s for record %s(%s).",
            getattr(salesperson, "name", "<unknown>"),
            getattr(salesperson, "id", "<none>"),
            sms_source,
            record._name,
            record.id,
        )
        ok, err = self._send_sales_team_sms(
            salesperson=salesperson,
            supervisor=supervisor,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source=sms_source,
            is_existing=True,
            lead=None,
        )
        if ok:
            try:
                update_vals = {"state_crm": "sent"}
                if "wing_sms_sent" in record._fields:
                    update_vals["wing_sms_sent"] = True
                record.sudo().write(update_vals)
            except Exception:
                pass
        else:
            _logger.warning(
                "Wing existing customer SMS: failed for record %s(%s) salesperson %s (id=%s): %s",
                record._name,
                record.id,
                getattr(salesperson, "name", "<unknown>"),
                getattr(salesperson, "id", "<none>"),
                err,
            )
            try:
                update_vals = {"state_crm": "draft"}
                if "wing_duplicate_popup_pending" in record._fields:
                    update_vals["wing_duplicate_popup_pending"] = True
                record.sudo().write(update_vals)
            except Exception:
                pass
        return ok, err

    @api.model
    def send_for_record_in_background(self, model_name, res_id, source):
        """
        Send SMS in a background thread so the HTTP request returns immediately.
        Uses a new cursor; on failure sets state_crm back to 'draft'.
        Deduplicates: skips if already sent for this (model_name, res_id) in the last 60 seconds.
        """
        import odoo
        key = (model_name, res_id)
        now = time.time()
        if key in _sms_sent_recently:
            last = _sms_sent_recently[key]
            if now - last < _SMS_COOLDOWN_SEC:
                _logger.info(
                    "Wing: skip duplicate SMS for %s id=%s (sent %.0fs ago)",
                    model_name, res_id, now - last,
                )
                return
        _sms_sent_recently[key] = now
        # Clean old entries
        cutoff = now - _SMS_COOLDOWN_SEC
        for k in list(_sms_sent_recently.keys()):
            if _sms_sent_recently[k] < cutoff:
                del _sms_sent_recently[k]

        dbname = self.env.cr.dbname
        registry = odoo.registry(dbname)

        def _run():
            try:
                # Use a fresh environment for the background thread so we
                # never interfere with the original HTTP/env objects.
                with registry.cursor() as cr:
                    env_bg = api.Environment(cr, self.env.uid, dict(self.env.context))
                    record_bg = env_bg[model_name].browse(res_id)
                    if not record_bg.exists():
                        return
                    wiz = env_bg["wing.existing.customer.sms"].create({})
                    success, err_msg = wiz.send_for_record(record_bg, source)
                    update_vals = {}
                    if success:
                        update_vals["state_crm"] = "sent"
                        update_vals["wing_sms_sent"] = True
                        # Preserve the pending popup flag if it was already set.
                        if "wing_duplicate_popup_pending" in record_bg._fields and record_bg.wing_duplicate_popup_pending:
                            update_vals["wing_duplicate_popup_pending"] = True
                    else:
                        update_vals["state_crm"] = "draft"
                        update_vals["wing_duplicate_popup_pending"] = True
                    try:
                        record_bg.sudo().write(update_vals)
                    except Exception:
                        pass
                    if not success:
                        _logger.warning(
                            "Wing: background SMS for %s id=%s failed: %s",
                            model_name, res_id, err_msg,
                        )
                    cr.commit()
            except Exception as e:
                _logger.exception("Wing: background SMS for %s id=%s failed: %s", model_name, res_id, e)
                try:
                    with registry.cursor() as cr2:
                        env_bg_err = api.Environment(cr2, self.env.uid, dict(self.env.context))
                        record_bg_err = env_bg_err[model_name].browse(res_id)
                        if record_bg_err.exists():
                            record_bg_err.write({"state_crm": "draft"})
                        cr2.commit()
                except Exception:
                    pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
