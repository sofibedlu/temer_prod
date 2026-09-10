# -*- coding: utf-8 -*-
# Wing Distribution: Website and Call Center (6033) – same algorithm as reception, no SMS for testing.
# Only in wing_distribution_configuration; do not modify crm_custom_menu.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


def _norm_phone(val):
    if not val or not str(val).strip():
        return None
    p = str(val).strip()
    # Normalize to digits only: keep international numbers (e.g. +1) and local numbers.
    digits = "".join(ch for ch in p if ch.isdigit())
    if not digits:
        return None
    # Trim leading 0 for local formats (e.g. 0912345678 -> 912345678)
    if digits.startswith("0") and len(digits) > 9:
        digits = digits[1:]
    return digits if len(digits) >= 9 else None


def _has_phone_in_vals(vals, phone_key="new_phone"):
    if _norm_phone(vals.get(phone_key)):
        return True
    fp = vals.get("full_phone")
    if fp and isinstance(fp, (list, tuple)):
        for cmd in fp:
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2:
                if cmd[0] == 4:
                    return True
                if cmd[0] == 6 and len(cmd) >= 3 and cmd[2]:
                    return True
                if cmd[0] == 0 and len(cmd) >= 3 and isinstance(cmd[2], dict):
                    if _norm_phone(cmd[2].get("name")):
                        return True
    return False


def _run_phone_country_backfill(env):
    """Run one-time backfill of country_id on crm.callcenter.phone (runs on module load)."""
    from .phone_country_backfill import backfill_callcenter_phone_country

    backfill_callcenter_phone_country(env)


def _get_full_phone_number_from_vals(vals, phone_key="new_phone"):
    """Return +251 formatted phone from vals for duplicate check, or None."""
    raw = vals.get(phone_key)
    if raw and str(raw).strip():
        p = str(raw).strip()
        if p.startswith("+251"):
            p = p[4:]
        elif p.startswith("251"):
            p = p[3:]
        if p.startswith("0"):
            p = p[1:]
        if p and len(p) >= 9:
            return f"+251{p}"
    return None


def _is_duplicate_before_create(env, raw_phone):
    """
    Pre-create duplicate detection so existing customers do NOT consume distribution slots.

    Treat as EXISTING customer when the phone is already known either in:
    - temer.phone (Customer Phones tab), OR
    - temer.lead / old crm.lead (via wing.duplicate.phone.mixin)
    """
    if not raw_phone or not str(raw_phone).strip():
        return False
    raw = str(raw_phone).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return False

    # If user provided +..., keep it as E164 candidate; otherwise we can only use tail matching.
    e164 = f"+{digits}" if raw.startswith("+") else None
    tail = digits[-10:] if len(digits) >= 10 else (digits[-9:] if len(digits) >= 9 else None)

    # 1) temer.phone is authoritative for "existing customer" in Wing (any country)
    if "temer.phone" in env:
        Phone = env["temer.phone"].sudo()
        if e164 and tail:
            domain = ["|", ("phone", "=", e164), ("phone", "ilike", tail)]
        elif e164:
            domain = [("phone", "=", e164)]
        elif tail:
            domain = ["|", ("phone", "=", raw), ("phone", "ilike", tail)]
        else:
            domain = [("phone", "=", raw)]
        if domain and Phone.search_count(domain):
            return True

    # 2) Also treat as existing if found in temer.lead or old crm.lead (best-effort; depends on data formats)
    try:
        if "wing.duplicate.phone.mixin" in env:
            candidate = e164 or raw
            sp, _sup, _msg = env["wing.duplicate.phone.mixin"].sudo()._wing_find_existing_temer_and_old_crm_only(candidate)
            if sp:
                return True
    except Exception:
        pass

    return False


# Cache for 6033 user between _get_next_available_supervisor_and_wing and _get_next_available_salesperson
# (Odoo records don't support arbitrary attributes like setattr)
_wing_6033_user_cache = {}


class CrmWebsiteWingDistribution(models.Model):
    _name = "crm.website"
    _inherit = ["crm.website", "wing.duplicate.phone.mixin", "wing.sales.team.sms.mixin"]
    wing_duplicate_popup_pending = fields.Boolean(
        string="Duplicate Popup Pending",
        default=False,
        copy=False,
        help="Internal flag: show duplicate popup once after detecting existing customer.",
    )

    @api.onchange("new_phone")
    def _onchange_new_phone_duplicate_check(self):
        if self.new_phone:
            raw = self.new_phone.strip()
            msg = self._get_duplicate_phone_message(raw)
            if msg:
                self.phone_number_message = msg
                return {"warning": {"title": _("Customer already registered"), "message": msg}}
            else:
                self.phone_number_message = False

    def _send_sms_for_duplicate(self):
        """
        Existing customer (duplicate phone) should send SMS via wing.existing.customer.sms.
        """
        self.ensure_one()
        return self._send_sms_to_existing_sales_team()

    def _create_temer_lead_automatically(self):
        """Wing: Base clears new_phone before calling; run full lead+SMS using full_phone."""
        self.ensure_one()
        raw_phone = (self.new_phone or "").strip() if self.new_phone else None
        if not raw_phone and self.full_phone:
            raw_phone = (self.full_phone[0].name or "").strip()
        if not raw_phone:
            return super()._create_temer_lead_automatically()

        def _normalize_phone(p):
            if not p or not str(p).strip():
                return None
            digits = "".join(ch for ch in str(p) if ch.isdigit())
            if not digits:
                return None
            # Trim leading 251 or 0 for local formats
            if digits.startswith("251"):
                digits = digits[3:]
            if digits.startswith("0"):
                digits = digits[1:]
            return digits if len(digits) >= 9 else None

        clean_phone = _normalize_phone(raw_phone)
        if not clean_phone:
            return super()._create_temer_lead_automatically()
        if getattr(self, "phone_number_message", None) and (self.phone_number_message or "").strip():
            return
        if getattr(self, "existing_salesperson_id", None) and self.existing_salesperson_id:
            return
        if getattr(self, "existing_temer_lead_id", None) and self.existing_temer_lead_id:
            return
        # Hard guard: check by phone digits regardless of country_id being set or not.
        # Prevents creating a new temer.lead for an existing customer even when country_id is missing.
        if _is_duplicate_before_create(self.env, raw_phone):
            _logger.info(
                "Wing Distribution (Website): phone already exists, skipping new lead for id=%s.", self.id
            )
            try:
                self._wing_backfill_duplicate_owner_from_phone(raw_phone)
            except Exception:
                pass
            return
        if self.state_crm != "draft" or not self.nominated_salesperson_id:
            return super()._create_temer_lead_automatically()
        if not self.customer_name or not self.customer_name.strip():
            return super()._create_temer_lead_automatically()
        # Safeguard: phone already in temer.phone → treat as duplicate, avoid ValidationError from temer.lead create
        if self.country_id and self.country_id.phone_code:
            country_code = str(self.country_id.phone_code or "").strip()
            if clean_phone.startswith(country_code):
                formatted_phone = f"+{clean_phone}"
            else:
                formatted_phone = f"+{country_code}{clean_phone}"
            existing_phone = self.env["temer.phone"].search([("phone", "=", formatted_phone)], limit=1)
            if existing_phone and existing_phone.lead_id:
                lead = existing_phone.lead_id
                _logger.info(
                    "Wing Distribution (Website): phone %s already in temer.phone; treating as duplicate for id=%s.",
                    formatted_phone,
                    self.id,
                )
                # Use the lead's user_id only if it is a real salesperson (has supervisor mapping).
                # If lead.user_id is the reception/website creator (no supervisor), fall back to
                # the wing duplicate mixin which searches temer.lead by phone more reliably.
                lead_user = getattr(lead, "user_id", None)
                existing_salesperson = None
                if lead_user and self._wing_user_has_supervisor(lead_user):
                    existing_salesperson = lead_user
                if not existing_salesperson:
                    # Try the mixin lookup which is more reliable
                    sp, _sup, _msg = self._wing_find_existing_temer_and_old_crm_only(formatted_phone)
                    if sp and self._wing_user_has_supervisor(sp):
                        existing_salesperson = sp
                msg = self._wing_duplicate_message_for_salesperson(existing_salesperson) if existing_salesperson else _(
                    "Customer is already registered."
                )
                duplicate_vals = {
                    "nominated_salesperson_id": False,
                    "nominated_wing_id": False,
                    "nominated_supervisor_id": False,
                    "assigned_salesperson_id": False,
                    "assigned_wing_id": False,
                    "assigned_supervisor_id": False,
                    "state_crm": "sent",
                    "wing_sms_sent": False,
                    "phone_number_message": msg,
                    "wing_duplicate_popup_pending": True,
                }
                if existing_salesperson and "existing_salesperson_id" in self._fields:
                    duplicate_vals["existing_salesperson_id"] = existing_salesperson.id
                if lead and "existing_temer_lead_id" in self._fields:
                    duplicate_vals["existing_temer_lead_id"] = lead.id
                if existing_salesperson and hasattr(self, "_get_supervisor_for_salesperson"):
                    sup = self._get_supervisor_for_salesperson(existing_salesperson)
                    if sup and "existing_supervisor_id" in self._fields and getattr(sup, "_name", None) == "property.sales.supervisor":
                        duplicate_vals["existing_supervisor_id"] = sup.id

                self.write(duplicate_vals)
                env = self.env
                model_name, res_id, src = self._name, self.id, "Website"

                # If existing salesperson has a phone, attempt immediate send (more reliable than waiting for postcommit).
                if existing_salesperson and self._wing_user_has_phone(existing_salesperson):
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            self, src
                        )
                        if success:
                            self.write({"state_crm": "sent", "wing_sms_sent": True})
                            return
                        _logger.warning(
                            "Wing Distribution (Website): existing-customer SMS failed for id=%s: %s",
                            self.id,
                            err_msg or "unknown",
                        )
                    except Exception:
                        _logger.exception(
                            "Wing Distribution (Website): error sending existing-customer SMS immediately for id=%s.",
                            self.id,
                        )

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(model_name, res_id, src)

                env.cr.postcommit.add(_schedule_sms)
                return
        source_id = self.source_id.id or self.env["utm.source"].search([("name", "=", "Website")], limit=1).id
        lead_values = {
            "name": self.name or f"Lead from {self.customer_name.strip()}",
            "customer_name": self.customer_name.strip(),
            "phone_no": clean_phone,
            "site_ids": [(6, 0, self.site_ids.ids)],
            "country_id": self.country_id.id,
            "source_ids": source_id,
            "user_id": self.nominated_salesperson_id.id,
            "state": "prospect",
            "from_website": True,
        }
        lead = False
        try:
            lead = self.env["temer.lead"].sudo().with_context(
                mail_create_nosubscribe=True, mail_create_nolog=True, tracking_disable=True
            ).create(lead_values)
            _logger.info("Wing Distribution (Website): creating lead and sending SMS for id=%s", self.id)
            sup = getattr(self, "nominated_supervisor_id", False) and self.nominated_supervisor_id
            if not sup and hasattr(self, "_get_supervisor_for_salesperson"):
                sup = self._get_supervisor_for_salesperson(self.nominated_salesperson_id)
            if not sup:
                sup = self.env["property.sales.supervisor"].search(
                    [("name", "=", self.nominated_salesperson_id.id)], limit=1
                )
            if not sup:
                mapping = self.env["property.salesperson.mapping"].search(
                    [("user_id", "=", self.nominated_salesperson_id.id)], limit=1
                )
                sup = mapping.supervisor_id if mapping else False
            self.write({"nominated_supervisor_id": sup.id if sup else False})
            sales_ok, err_msg = self._send_sales_team_sms_from_record(
                source="Website",
                is_existing=False,
                lead=lead,
                customer_phone_override=clean_phone,
            )
            if not sales_ok:
                _logger.warning(
                    "Wing Distribution (Website): SMS reported failure for id=%s (%s). Lead kept; not blocking.",
                    self.id,
                    err_msg or "unknown",
                )
            write_vals = {
                "assigned_salesperson_id": self.nominated_salesperson_id.id,
                "assigned_wing_id": self.nominated_wing_id.id if self.nominated_wing_id else False,
                "assigned_supervisor_id": sup.id if sup else False,
            }
            if sales_ok:
                write_vals["state_crm"] = "sent"
            self.write(write_vals)
        except Exception as e:
            _logger.error("Wing Distribution (Website): error creating lead/SMS: %s", str(e))
            try:
                if lead:
                    lead.unlink()
            except Exception:
                _logger.exception("Wing Distribution (Website): failed to cleanup lead after error.")
            raise

    assigned_salesperson_name = fields.Char(
        string="Assigned Person Name",
        related="assigned_salesperson_id.partner_id.name",
        readonly=True,
    )
    assigned_supervisor_name = fields.Char(
        string="Assigned Person Supervisor",
        related="assigned_supervisor_id.name.name",
        readonly=True,
    )
    assigned_salesperson_phone = fields.Char(
        string="Assigned Person Phone",
        related="assigned_salesperson_id.partner_id.phone",
        readonly=True,
    )

    assigned_via_wing_distribution = fields.Boolean(
        string="Assigned via Wing Distribution",
        default=False,
        readonly=True,
        copy=False,
    )

    def _has_active_distribution_lines(self, type_code):
        """True if there is at least one active distribution line for this type. Uses sudo so lead save does not require Wing Distribution access."""
        dist_type = self.env["wing.distribution.type"].sudo().search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = self.env["wing.distribution.type"].sudo().search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            return False
        return bool(
            self.env["wing.distribution.line"].sudo().search_count(
                [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
            )
        )

    def _has_active_website_distribution_lines(self):
        return self._has_active_distribution_lines("website")

    def _get_active_website_users(self):
        """Return users from active Website distribution lines. Uses mixin so no Reception record needed."""
        return self._get_active_distribution_users("website")

    def _get_next_user_by_weighted_team(self, type_code="website"):
        """
        Use mixin (same algorithm as Reception); works without any Reception record.
        HARD GUARD: if this record is a duplicate (existing customer), do NOT
        consume any distribution slot here either.
        """
        # Context flag from pre-create duplicate check
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (Website): _get_next_user_by_weighted_team skipped due to duplicate-phone context."
            )
            return False, False
        # Runtime duplicate safety: if phone already exists in temer.phone, skip
        try:
            raw = ""
            if getattr(self, "new_phone", None):
                raw = (self.new_phone or "").strip()
            if not raw and getattr(self, "full_phone", None) and self.full_phone:
                raw = (self.full_phone[0].name or "").strip()
            if raw and _is_duplicate_before_create(self.env, raw):
                _logger.info(
                    "Wing Distribution (Website): _get_next_user_by_weighted_team runtime duplicate %s, skipping.",
                    raw,
                )
                return False, False
        except Exception:
            pass
        return super()._get_next_user_by_weighted_team(type_code)

    def _get_next_available_rr_user_and_config(self):
        # Important: when phone is duplicate, skip distribution to avoid serving a line.
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (Website): skipping distribution due to duplicate-phone precheck (context flag)."
            )
            return (False, False)
        # Extra safety: if this record's phone is already registered, do not serve any line.
        raw = ""
        if getattr(self, "new_phone", None):
            raw = (self.new_phone or "").strip()
        if not raw and getattr(self, "full_phone", None) and self.full_phone:
            raw = (self.full_phone[0].name or "").strip()
        if raw and _is_duplicate_before_create(self.env, raw):
            _logger.info(
                "Wing Distribution (Website): runtime duplicate detected for %s, skipping distribution.",
                raw,
            )
            return (False, False)
        if self._has_active_website_distribution_lines():
            _logger.info("Wing Distribution (Website): using weighted assignment (website type active).")
            return self._get_next_user_by_weighted_team("website")
        _logger.info("Wing Distribution (Website): no config or no active users in wing config; not nominating.")
        return (False, False)

    _NO_CONFIG_MESSAGE = (
        "No wing config or no active users in wing config. No assignment made (wing distribution only)."
    )

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        return super(CrmWebsiteWingDistribution, self)._get_duplicate_phone_message(full_phone_number, exclude_ids)

    def _get_existing_salesperson_info(self, full_phone_number):
        return super(CrmWebsiteWingDistribution, self)._get_existing_salesperson_info(full_phone_number)

    def _send_sms_to_existing_sales_team(self):
        """Use wing.existing.customer.sms model only (no crm_custom_menu logic). 1 or 2 SMS."""
        wiz = self.env["wing.existing.customer.sms"].create({})
        return wiz.send_for_record(self, "Website")

    def action_send_sms_to_existing_customer(self):
        """Same as Reception: send 1 or 2 SMS via wing.existing.customer.sms; raise on failure."""
        self.ensure_one()
        if not getattr(self, "phone_number_message", None) or not self.phone_number_message.strip():
            raise ValidationError(_("No duplicate phone information. This record has no existing salesperson."))
        success, err_msg = self._send_sms_to_existing_sales_team()
        if not success:
            raise ValidationError(
                err_msg or _("SMS could not be sent. Please check the SMS gateway or contact IT.")
            )
        self.write({"state_crm": "sent"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("SMS Sent"),
                "message": _("SMS sent to existing salesperson and supervisor (if different)."),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("Wing Distribution (Website): crm.website create called, count=%s.", len(vals_list))
        # Require phone number before save - block create completely if no phone
        for vals in vals_list:
            if not _has_phone_in_vals(vals, "new_phone"):
                raise UserError(_("Please insert a phone number."))
        # Validation: block save when no active wing config (show error, do not use old algo)
        if not self._has_active_website_distribution_lines():
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Website. "
                    "Please add Website distribution type with active users in Wing Distribution, or activate existing lines. Lead not created."
                )
            )
        users = self._get_active_website_users()
        if not users:
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Website. "
                    "Please add users to Website distribution lines or activate them. Lead not created."
                )
            )
        # Create one-by-one so we can release distribution slots for duplicates and never "serve" them.
        records = self.env["crm.website"]
        for vals in vals_list:
            raw = (vals.get("new_phone") or "").strip() if vals.get("new_phone") else ""
            if not raw and vals.get("full_phone"):
                try:
                    fp = vals.get("full_phone")
                    if fp and isinstance(fp, (list, tuple)):
                        for cmd in fp:
                            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 0 and isinstance(cmd[2], dict):
                                raw = (cmd[2].get("name") or "").strip()
                                if raw:
                                    break
                except Exception:
                    raw = raw or ""
            
            is_dup_pre = _is_duplicate_before_create(self.env, raw) if raw else False
            ctx = dict(self.env.context)
            if is_dup_pre:
                ctx["wing_skip_distribution_for_duplicate"] = True
            
            rec = super(CrmWebsiteWingDistribution, self.with_context(ctx)).create(vals)
            records |= rec

        for rec in records:
            # Update phone country if missing (compatibility with crm_custom_menu)
            if rec.full_phone and rec.country_id:
                for phone in rec.full_phone:
                    if not phone.country_id:
                        phone.country_id = rec.country_id.id
            
            raw = (rec.new_phone or "").strip() if getattr(rec, "new_phone", None) else ""
            if not raw and getattr(rec, "full_phone", None) and rec.full_phone:
                raw = (rec.full_phone[0].name or "").strip()
            
            # Backfill existing owner info if duplicate
            is_duplicate = False
            if raw:
                is_duplicate = rec._wing_backfill_duplicate_owner_from_phone(raw)
            
            if is_duplicate:
                # Release distribution slot if this was a walk-in/nominated duplicate
                try:
                    rec._wing_release_distribution_slot("Website")
                except Exception:
                    pass

                existing_salesperson = getattr(rec, "existing_salesperson_id", None) and rec.existing_salesperson_id
                msg = rec.phone_number_message or rec._wing_duplicate_message_for_salesperson(existing_salesperson)
                
                rec.write({
                    "nominated_salesperson_id": False,
                    "nominated_wing_id": False,
                    "nominated_supervisor_id": False,
                    "assigned_salesperson_id": False,
                    "assigned_wing_id": False,
                    "assigned_supervisor_id": False,
                    "state_crm": "sent",
                    "phone_number_message": msg,
                    "wing_duplicate_popup_pending": True,
                    "wing_sms_sent": False,
                })
                
                model_name, res_id, src = rec._name, rec.id, "Website"
                env = rec.env

                # Immediate SMS attempt (like Reception)
                if existing_salesperson and rec._wing_user_has_phone(existing_salesperson):
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            rec, src
                        )
                        if success:
                            rec.write({"state_crm": "sent", "wing_sms_sent": True})
                            continue
                        _logger.warning(
                            "Wing Distribution (Website): existing-customer SMS failed for id=%s: %s",
                            rec.id, err_msg or "unknown"
                        )
                    except Exception:
                        _logger.exception("Wing Distribution (Website): error sending existing-customer SMS immediately for id=%s.", rec.id)

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(
                        model_name, res_id, src
                    )
                env.cr.postcommit.add(_schedule_sms)
                continue
            
            # Normal assignment logic if not duplicate
            if rec._has_active_website_distribution_lines() and rec.nominated_salesperson_id:
                super(CrmWebsiteWingDistribution, rec).write({
                    "assigned_salesperson_id": rec.nominated_salesperson_id.id,
                    "assigned_via_wing_distribution": True,
                })
                _logger.info(
                    "Wing Distribution (Website): id=%s assigned_salesperson_id=%s.",
                    rec.id,
                    rec.nominated_salesperson_id.name,
                )
            # Message disabled for now - avoid errors like before
            # elif not rec._has_active_website_distribution_lines():
            #     try:
            #         rec.message_post(
            #             body=self._NO_CONFIG_MESSAGE,
            #             message_type="notification",
            #             subtype_xmlid="mail.mt_note",
            #         )
            #     except Exception as e:
            #         _logger.warning(
            #             "Wing Distribution (Website): could not post no-config message on id=%s: %s",
            #             rec.id,
            #             e,
            #         )
        return records

    _WRITE_TRIGGER_KEYS = {"customer_name", "site_ids", "new_phone", "full_phone"}

    def write(self, vals):
        # Assignment only on create; on update do not run algorithm and do not set "served"
        if not vals:
            return True
        assignment_keys = {"nominated_salesperson_id", "assigned_salesperson_id"}
        if assignment_keys & set(vals):
            if any(
                rec._has_active_website_distribution_lines() and rec.nominated_salesperson_id
                for rec in self
            ):
                vals = dict(vals, assigned_via_wing_distribution=True)
            return super().write(vals)
        trigger_in_vals = self._WRITE_TRIGGER_KEYS & set(vals)
        # Block save when draft would have no phone after this write
        if trigger_in_vals:
            for rec in self:
                if getattr(rec, "state_crm", None) != "draft":
                    continue
                will_have_phone = bool(_norm_phone(vals.get("new_phone")))
                if "full_phone" in vals:
                    fp = vals["full_phone"]
                    if fp and isinstance(fp, (list, tuple)):
                        for cmd in fp:
                            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2:
                                if cmd[0] == 4 or (cmd[0] == 6 and len(cmd) >= 3 and cmd[2]):
                                    will_have_phone = True
                                    break
                                if cmd[0] == 0 and len(cmd) >= 3 and isinstance(cmd[2], dict) and _norm_phone(cmd[2].get("name")):
                                    will_have_phone = True
                                    break
                if not will_have_phone:
                    has_existing = bool(rec.full_phone) or bool(_norm_phone(getattr(rec, "new_phone", None)))
                    if not has_existing:
                        raise UserError(_("Please insert a phone number."))
        # On duplicate we allow save; form shows existing salesperson; popup "Customer is already registered" (JS)
        preserve = trigger_in_vals and any(
            rec._has_active_website_distribution_lines()
            and (rec.nominated_salesperson_id or rec.assigned_salesperson_id)
            for rec in self
        )
        if preserve:
            other_vals = {k: v for k, v in vals.items() if k not in self._WRITE_TRIGGER_KEYS}
            trigger_vals = {k: vals[k] for k in trigger_in_vals}
            vals_to_base = dict(other_vals)
            if "new_phone" in vals:
                vals_to_base["new_phone"] = vals["new_phone"]
            if "full_phone" in vals:
                vals_to_base["full_phone"] = vals["full_phone"]
            res = super().write(vals_to_base)
            trigger_vals_safe = {
                k: v for k, v in trigger_vals.items()
                if getattr(self._fields.get(k), "column_type", None)
            }
            if "new_phone" in trigger_vals_safe:
                trigger_vals_safe["new_phone"] = ""
            trigger_vals_relation = {k: v for k, v in trigger_vals.items() if k not in trigger_vals_safe}
            if trigger_vals_safe:
                self._write(trigger_vals_safe)
            if trigger_vals_relation:
                for fname, value in trigger_vals_relation.items():
                    self._fields[fname].write(self, value)
            return res
        if any(rec._has_active_website_distribution_lines() and rec.nominated_salesperson_id for rec in self):
            vals = dict(vals, assigned_via_wing_distribution=True)
        res = super().write(vals)
        # Clear new_phone after normal write
        if vals.get("new_phone"):
            self._write({"new_phone": ""})
        return res

    def action_add_phone_and_save(self):
        """Action for the 'Add/Save' button next to the phone field."""
        self.ensure_one()
        self.write({})
        return True


class CrmCallCenterWingDistribution(models.Model):
    _name = "crm.callcenter"
    _inherit = ["crm.callcenter", "wing.duplicate.phone.mixin", "wing.sales.team.sms.mixin"]
    wing_duplicate_popup_pending = fields.Boolean(
        string="Duplicate Popup Pending",
        default=False,
        copy=False,
        help="Internal flag: show duplicate popup once after detecting existing customer.",
    )

    @api.onchange("new_phone")
    def _onchange_new_phone_duplicate_check(self):
        if self.new_phone:
            raw = self.new_phone.strip()
            msg = self._get_duplicate_phone_message(raw)
            if msg:
                self.phone_number_message = msg
                return {"warning": {"title": _("Customer already registered"), "message": msg}}
            else:
                self.phone_number_message = False

    def _send_sms_for_duplicate(self):
        """
        Existing customer (duplicate phone) should send SMS via wing.existing.customer.sms.
        """
        self.ensure_one()
        return self._send_sms_to_existing_sales_team()

    def _create_temer_lead_automatically(self):
        """Wing: Base clears new_phone before calling; run full lead+SMS using full_phone."""
        self.ensure_one()
        raw_phone = (self.new_phone or "").strip() if self.new_phone else None
        if not raw_phone and self.full_phone:
            raw_phone = (self.full_phone[0].name or "").strip()
        if not raw_phone:
            return super()._create_temer_lead_automatically()

        def _normalize_phone(p):
            if not p or not str(p).strip():
                return None
            digits = "".join(ch for ch in str(p) if ch.isdigit())
            if not digits:
                return None
            # Trim leading 251 or 0 for local formats
            if digits.startswith("251"):
                digits = digits[3:]
            if digits.startswith("0"):
                digits = digits[1:]
            return digits if len(digits) >= 9 else None

        clean_phone = _normalize_phone(raw_phone)
        if not clean_phone:
            return super()._create_temer_lead_automatically()
        if getattr(self, "phone_number_message", None) and (self.phone_number_message or "").strip():
            return
        if getattr(self, "existing_salesperson_id", None) and self.existing_salesperson_id:
            return
        if getattr(self, "existing_temer_lead_id", None) and self.existing_temer_lead_id:
            return
        # Hard guard: check by phone digits regardless of country_id being set or not.
        # Prevents creating a new temer.lead for an existing customer even when country_id is missing.
        if _is_duplicate_before_create(self.env, raw_phone):
            _logger.info(
                "Wing Distribution (6033): phone already exists, skipping new lead for id=%s.", self.id
            )
            try:
                self._wing_backfill_duplicate_owner_from_phone(raw_phone)
            except Exception:
                pass
            return
        if self.state_crm != "draft" or not self.nominated_salesperson_id:
            return super()._create_temer_lead_automatically()
        if not self.customer_name or not self.customer_name.strip():
            return super()._create_temer_lead_automatically()
        # Safeguard: phone already in temer.phone → treat as duplicate, avoid ValidationError from temer.lead create
        if self.country_id and self.country_id.phone_code:
            country_code = str(self.country_id.phone_code or "").strip()
            if clean_phone.startswith(country_code):
                formatted_phone = f"+{clean_phone}"
            else:
                formatted_phone = f"+{country_code}{clean_phone}"
            existing_phone = self.env["temer.phone"].search([("phone", "=", formatted_phone)], limit=1)
            if existing_phone and existing_phone.lead_id:
                lead = existing_phone.lead_id
                _logger.info(
                    "Wing Distribution (6033): phone %s already in temer.phone; treating as duplicate for id=%s.",
                    formatted_phone,
                    self.id,
                )
                # Use lead.user_id only if it is a real salesperson (has supervisor mapping).
                # If it's the creator/reception user (no supervisor), use the mixin lookup instead.
                lead_user = getattr(lead, "user_id", None)
                existing_salesperson = None
                if lead_user and self._wing_user_has_supervisor(lead_user):
                    existing_salesperson = lead_user
                if not existing_salesperson:
                    sp, _sup, _msg = self._wing_find_existing_temer_and_old_crm_only(formatted_phone)
                    if sp and self._wing_user_has_supervisor(sp):
                        existing_salesperson = sp
                duplicate_vals = {
                    "nominated_salesperson_id": False,
                    "nominated_wing_id": False,
                    "nominated_supervisor_id": False,
                    "assigned_salesperson_id": False,
                    "assigned_wing_id": False,
                    "assigned_supervisor_id": False,
                    "state_crm": "sent",
                    "wing_sms_sent": False,
                }
                if existing_salesperson and "existing_salesperson_id" in self._fields:
                    duplicate_vals["existing_salesperson_id"] = existing_salesperson.id
                if existing_salesperson and "existing_temer_lead_id" in self._fields:
                    duplicate_vals["existing_temer_lead_id"] = lead.id
                if existing_salesperson and hasattr(self, "_get_supervisor_for_salesperson"):
                    sup = self._get_supervisor_for_salesperson(existing_salesperson)
                    if sup and "existing_supervisor_id" in self._fields and getattr(sup, "_name", None) == "property.sales.supervisor":
                        duplicate_vals["existing_supervisor_id"] = sup.id
                if "phone_number_message" in self._fields:
                    duplicate_vals["phone_number_message"] = _("Customer is already registered.")
                if "wing_duplicate_popup_pending" in self._fields:
                    duplicate_vals["wing_duplicate_popup_pending"] = True
                self.write(duplicate_vals)
                env = self.env
                model_name, res_id, src = self._name, self.id, "Call Center (6033)"

                if existing_salesperson and self._wing_user_has_phone(existing_salesperson):
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            self, src
                        )
                        if success:
                            self.write({"state_crm": "sent", "wing_sms_sent": True})
                            return
                        _logger.warning(
                            "Wing Distribution (6033): existing-customer SMS failed for id=%s: %s",
                            self.id,
                            err_msg or "unknown",
                        )
                    except Exception:
                        _logger.exception(
                            "Wing Distribution (6033): error sending existing-customer SMS immediately for id=%s.",
                            self.id,
                        )

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(model_name, res_id, src)

                env.cr.postcommit.add(_schedule_sms)
                return
        source_id = self.source_id.id or self.env["utm.source"].search([("name", "=", "6033")], limit=1).id
        lead_values = {
            "name": self.name or f"Lead from {self.customer_name.strip()}",
            "customer_name": self.customer_name.strip(),
            "phone_no": clean_phone,
            "site_ids": [(6, 0, self.site_ids.ids)],
            "country_id": self.country_id.id,
            "source_ids": source_id,
            "user_id": self.nominated_salesperson_id.id,
            "state": "prospect",
        }
        if hasattr(self.env["temer.lead"], "from_callcenter"):
            lead_values["from_callcenter"] = True
        lead = False
        try:
            lead = self.env["temer.lead"].sudo().with_context(
                mail_create_nosubscribe=True, mail_create_nolog=True, tracking_disable=True
            ).create(lead_values)
            _logger.info("Wing Distribution (6033): creating lead and sending SMS for id=%s", self.id)
            sup = getattr(self, "nominated_supervisor_id", False) and self.nominated_supervisor_id
            if not sup and hasattr(self, "_get_supervisor_for_salesperson"):
                sup = self._get_supervisor_for_salesperson(self.nominated_salesperson_id)
            if not sup:
                sup = self.env["property.sales.supervisor"].search(
                    [("name", "=", self.nominated_salesperson_id.id)], limit=1
                )
            if not sup:
                mapping = self.env["property.salesperson.mapping"].search(
                    [("user_id", "=", self.nominated_salesperson_id.id)], limit=1
                )
                sup = mapping.supervisor_id if mapping else False
            self.write({"nominated_supervisor_id": sup.id if sup else False})
            sales_ok, err_msg = self._send_sales_team_sms_from_record(
                source="Call Center (6033)",
                is_existing=False,
                lead=lead,
                customer_phone_override=clean_phone,
            )
            if not sales_ok:
                _logger.warning(
                    "Wing Distribution (6033): SMS reported failure for id=%s (%s). Lead kept; not blocking.",
                    self.id,
                    err_msg or "unknown",
                )
            write_vals = {
                "assigned_salesperson_id": self.nominated_salesperson_id.id,
                "assigned_wing_id": self.nominated_wing_id.id if self.nominated_wing_id else False,
                "assigned_supervisor_id": sup.id if sup else False,
            }
            if sales_ok:
                write_vals["state_crm"] = "sent"
            self.write(write_vals)
        except Exception as e:
            _logger.error("Wing Distribution (6033): error creating lead/SMS: %s", str(e))
            try:
                if lead:
                    lead.unlink()
            except Exception:
                _logger.exception("Wing Distribution (6033): failed to cleanup lead after error.")
            raise

    assigned_salesperson_name = fields.Char(
        string="Assigned Person Name",
        related="assigned_salesperson_id.partner_id.name",
        readonly=True,
    )
    assigned_supervisor_name = fields.Char(
        string="Assigned Person Supervisor",
        related="assigned_supervisor_id.name.name",
        readonly=True,
    )
    assigned_salesperson_phone = fields.Char(
        string="Assigned Person Phone",
        related="assigned_salesperson_id.partner_id.phone",
        readonly=True,
    )

    assigned_via_wing_distribution = fields.Boolean(
        string="Assigned via Wing Distribution",
        default=False,
        readonly=True,
        copy=False,
    )

    def _has_active_distribution_lines(self, type_code):
        """True if there is at least one active distribution line for this type. Uses sudo so lead save does not require Wing Distribution access."""
        dist_type = self.env["wing.distribution.type"].sudo().search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = self.env["wing.distribution.type"].sudo().search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            return False
        return bool(
            self.env["wing.distribution.line"].sudo().search_count(
                [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
            )
        )

    def _has_active_6033_distribution_lines(self):
        return self._has_active_distribution_lines("6033")

    def _get_active_6033_users(self):
        """Return users from active 6033 distribution lines. Uses mixin so no Reception record needed."""
        return self._get_active_distribution_users("6033")

    def _get_next_user_by_weighted_team(self, type_code="6033"):
        """
        Use mixin (same algorithm as Reception); works without any Reception record.
        HARD GUARD: if this record is a duplicate (existing customer), do NOT
        consume any distribution slot here either.
        """
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (6033): _get_next_user_by_weighted_team skipped due to duplicate-phone context."
            )
            return False, False
        try:
            raw = ""
            if getattr(self, "new_phone", None):
                raw = (self.new_phone or "").strip()
            if not raw and getattr(self, "full_phone", None) and self.full_phone:
                raw = (self.full_phone[0].name or "").strip()
            if raw and _is_duplicate_before_create(self.env, raw):
                _logger.info(
                    "Wing Distribution (6033): _get_next_user_by_weighted_team runtime duplicate %s, skipping.",
                    raw,
                )
                return False, False
        except Exception:
            pass
        return super()._get_next_user_by_weighted_team(type_code)

    def _get_next_available_supervisor_and_wing(self):
        # For existing customers (duplicate phone), DO NOT run wing distribution at all.
        # This keeps the algorithm strictly for new leads and prevents "served" lines
        # from being consumed by duplicates.
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (6033): skipping supervisor/wing selection due to duplicate-phone context flag."
            )
            return super()._get_next_available_supervisor_and_wing()
        raw = ""
        if getattr(self, "new_phone", None):
            raw = (self.new_phone or "").strip()
        if not raw and getattr(self, "full_phone", None) and self.full_phone:
            raw = (self.full_phone[0].name or "").strip()
        if raw and _is_duplicate_before_create(self.env, raw):
            _logger.info(
                "Wing Distribution (6033): runtime duplicate detected for %s, skipping supervisor/wing selection.",
                raw,
            )
            return super()._get_next_available_supervisor_and_wing()
        if not self._has_active_6033_distribution_lines():
            return super()._get_next_available_supervisor_and_wing()
        _logger.info("Wing Distribution (6033): using weighted assignment (6033 type active).")
        user, config = self._get_next_user_by_weighted_team("6033")
        if not user:
            return super()._get_next_available_supervisor_and_wing()
        # Find supervisor for this user (same as reception)
        sup = self.env["property.sales.supervisor"].search([("name", "=", user.id)], limit=1)
        if not sup:
            mapping = self.env["property.salesperson.mapping"].search([("user_id", "=", user.id)], limit=1)
            sup = mapping.supervisor_id if mapping else False
        # Store user so _get_next_available_salesperson can return it (same request)
        _wing_6033_user_cache[("crm.callcenter", self.id)] = user.id
        _logger.info("Wing Distribution (6033): nominated user=%s supervisor=%s config=%s.", user.name, sup.name if sup else None, config.display_name if config else None)
        return (sup, config) if sup else (False, config)

    def _get_next_available_salesperson(self, supervisor):
        if self._has_active_6033_distribution_lines():
            key = ("crm.callcenter", self.id)
            user_id = _wing_6033_user_cache.pop(key, None)
            if user_id:
                return self.env["res.users"].browse(user_id)
        return super()._get_next_available_salesperson(supervisor)

    def _get_next_available_rr_user_and_config(self):
        """Use weighted 6033 distribution when active; else do not nominate."""
        # Important: when phone is duplicate, skip distribution to avoid serving a line.
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (6033): skipping distribution due to duplicate-phone precheck (context flag)."
            )
            return (False, False)
        # Extra safety: if this record's phone is already registered, do not serve any line.
        raw = ""
        if getattr(self, "new_phone", None):
            raw = (self.new_phone or "").strip()
        if not raw and getattr(self, "full_phone", None) and self.full_phone:
            raw = (self.full_phone[0].name or "").strip()
        if raw and _is_duplicate_before_create(self.env, raw):
            _logger.info(
                "Wing Distribution (6033): runtime duplicate detected for %s, skipping distribution.",
                raw,
            )
            return (False, False)
        if self._has_active_6033_distribution_lines():
            _logger.info("Wing Distribution (6033): using weighted assignment in create (6033 type active).")
            return self._get_next_user_by_weighted_team("6033")
        _logger.info("Wing Distribution (6033): no config or no active users in wing config; not nominating.")
        return (False, False)

    _NO_CONFIG_MESSAGE_6033 = (
        "No wing config or no active users in wing config. No assignment made (wing distribution only)."
    )

    @api.model
    def _register_hook(self):
        super()._register_hook()
        _run_phone_country_backfill(self.env)

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        return super(CrmCallCenterWingDistribution, self)._get_duplicate_phone_message(full_phone_number, exclude_ids)

    def _get_existing_salesperson_info(self, full_phone_number):
        return super(CrmCallCenterWingDistribution, self)._get_existing_salesperson_info(full_phone_number)

    def _send_sms_to_existing_sales_team(self):
        """Use wing.existing.customer.sms model only (no crm_custom_menu logic). 1 or 2 SMS."""
        wiz = self.env["wing.existing.customer.sms"].create({})
        return wiz.send_for_record(self, "Call Center (6033)")

    def action_send_sms_to_existing_customer(self):
        """Same as Reception: send 1 or 2 SMS via wing.existing.customer.sms; raise on failure."""
        self.ensure_one()
        if not getattr(self, "phone_number_message", None) or not self.phone_number_message.strip():
            raise ValidationError(_("No duplicate phone information. This record has no existing salesperson."))
        success, err_msg = self._send_sms_to_existing_sales_team()
        if not success:
            raise ValidationError(
                err_msg or _("SMS could not be sent. Please check the SMS gateway or contact IT.")
            )
        self.write({"state_crm": "sent"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("SMS Sent"),
                "message": _("SMS sent to existing salesperson and supervisor (if different)."),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("Wing Distribution (6033): crm.callcenter create called, count=%s.", len(vals_list))
        # Require phone number before save - block create completely if no phone
        for vals in vals_list:
            if not _has_phone_in_vals(vals, "new_phone"):
                raise UserError(_("Please insert a phone number."))
        # Validation: block save when no active wing config (show error, do not use old algo)
        if not self._has_active_6033_distribution_lines():
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Call Center (6033). "
                    "Please add 6033 distribution type with active users in Wing Distribution, or activate existing lines. Lead not created."
                )
            )
        users = self._get_active_6033_users()
        if not users:
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Call Center (6033). "
                    "Please add users to 6033 distribution lines or activate them. Lead not created."
                )
            )
        # Create one-by-one so we can release distribution slots for duplicates and never "serve" them.
        records = self.env["crm.callcenter"]
        for vals in vals_list:
            raw = (vals.get("new_phone") or "").strip() if vals.get("new_phone") else ""
            if not raw and vals.get("full_phone"):
                try:
                    fp = vals.get("full_phone")
                    if fp and isinstance(fp, (list, tuple)):
                        for cmd in fp:
                            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 0 and isinstance(cmd[2], dict):
                                raw = (cmd[2].get("name") or "").strip()
                                if raw:
                                    break
                except Exception:
                    raw = raw or ""
            
            is_dup_pre = _is_duplicate_before_create(self.env, raw) if raw else False
            ctx = dict(self.env.context)
            if is_dup_pre:
                ctx["wing_skip_distribution_for_duplicate"] = True
            
            rec = super(CrmCallCenterWingDistribution, self.with_context(ctx)).create(vals)
            records |= rec

        for rec in records:
            # Update phone country if missing (compatibility with crm_custom_menu)
            if rec.full_phone and rec.country_id:
                for phone in rec.full_phone:
                    if not phone.country_id:
                        phone.country_id = rec.country_id.id
            
            raw = (rec.new_phone or "").strip() if getattr(rec, "new_phone", None) else ""
            if not raw and getattr(rec, "full_phone", None) and rec.full_phone:
                raw = (rec.full_phone[0].name or "").strip()
            
            # Backfill existing owner info if duplicate
            is_duplicate = False
            if raw:
                is_duplicate = rec._wing_backfill_duplicate_owner_from_phone(raw)
            
            if is_duplicate:
                # Release distribution slot if this was a walk-in/nominated duplicate
                try:
                    rec._wing_release_distribution_slot("6033")
                except Exception:
                    pass

                existing_salesperson = getattr(rec, "existing_salesperson_id", None) and rec.existing_salesperson_id
                msg = rec.phone_number_message or rec._wing_duplicate_message_for_salesperson(existing_salesperson)
                
                rec.write({
                    "nominated_salesperson_id": False,
                    "nominated_wing_id": False,
                    "nominated_supervisor_id": False,
                    "assigned_salesperson_id": False,
                    "assigned_wing_id": False,
                    "assigned_supervisor_id": False,
                    "state_crm": "sent",
                    "phone_number_message": msg,
                    "wing_duplicate_popup_pending": True,
                    "wing_sms_sent": False,
                })
                
                model_name, res_id, src = rec._name, rec.id, "Call Center (6033)"
                env = rec.env

                # Immediate SMS attempt (like Reception)
                if existing_salesperson and rec._wing_user_has_phone(existing_salesperson):
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            rec, src
                        )
                        if success:
                            rec.write({"state_crm": "sent", "wing_sms_sent": True})
                            continue
                        _logger.warning(
                            "Wing Distribution (6033): existing-customer SMS failed for id=%s: %s",
                            rec.id, err_msg or "unknown"
                        )
                    except Exception:
                        _logger.exception("Wing Distribution (6033): error sending existing-customer SMS immediately for id=%s.", rec.id)

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(
                        model_name, res_id, src
                    )
                env.cr.postcommit.add(_schedule_sms)
                continue
            
            # Normal assignment logic if not duplicate
            if rec._has_active_6033_distribution_lines() and rec.nominated_salesperson_id:
                super(CrmCallCenterWingDistribution, rec).write({
                    "assigned_salesperson_id": rec.nominated_salesperson_id.id,
                    "assigned_via_wing_distribution": True,
                })
                _logger.info(
                    "Wing Distribution (6033): id=%s assigned_salesperson_id=%s.",
                    rec.id,
                    rec.nominated_salesperson_id.name,
                )
            # Message disabled for now - avoid errors like before
            # elif not rec._has_active_6033_distribution_lines():
            #     try:
            #         rec.message_post(
            #             body=self._NO_CONFIG_MESSAGE_6033,
            #             message_type="notification",
            #             subtype_xmlid="mail.mt_note",
            #         )
            #     except Exception as e:
            #         _logger.warning(
            #             "Wing Distribution (6033): could not post no-config message on id=%s: %s",
            #             rec.id,
            #             e,
            #         )
        return records

    _WRITE_TRIGGER_KEYS = {"customer_name", "site_ids", "new_phone", "full_phone"}

    def write(self, vals):
        # Assignment only on create; on update do not run algorithm and do not set "served"
        if not vals:
            return True
        assignment_keys = {"nominated_salesperson_id", "assigned_salesperson_id"}
        if assignment_keys & set(vals):
            if any(
                rec._has_active_6033_distribution_lines() and rec.nominated_salesperson_id
                for rec in self
            ):
                vals = dict(vals, assigned_via_wing_distribution=True)
            return super().write(vals)
        trigger_in_vals = self._WRITE_TRIGGER_KEYS & set(vals)
        # Block save when draft would have no phone after this write
        if trigger_in_vals:
            for rec in self:
                if getattr(rec, "state_crm", None) != "draft":
                    continue
                will_have_phone = bool(_norm_phone(vals.get("new_phone")))
                if "full_phone" in vals:
                    fp = vals["full_phone"]
                    if fp and isinstance(fp, (list, tuple)):
                        for cmd in fp:
                            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2:
                                if cmd[0] == 4 or (cmd[0] == 6 and len(cmd) >= 3 and cmd[2]):
                                    will_have_phone = True
                                    break
                                if cmd[0] == 0 and len(cmd) >= 3 and isinstance(cmd[2], dict) and _norm_phone(cmd[2].get("name")):
                                    will_have_phone = True
                                    break
                if not will_have_phone:
                    has_existing = bool(rec.full_phone) or bool(_norm_phone(getattr(rec, "new_phone", None)))
                    if not has_existing:
                        raise UserError(_("Please insert a phone number."))
        # On duplicate we allow save; form shows existing salesperson; popup "Customer is already registered" (JS)
        preserve = trigger_in_vals and any(
            rec._has_active_6033_distribution_lines()
            and (rec.nominated_salesperson_id or rec.assigned_salesperson_id)
            for rec in self
        )
        if preserve:
            other_vals = {k: v for k, v in vals.items() if k not in self._WRITE_TRIGGER_KEYS}
            trigger_vals = {k: vals[k] for k in trigger_in_vals}
            vals_to_base = dict(other_vals)
            if "new_phone" in vals:
                vals_to_base["new_phone"] = vals["new_phone"]
            if "full_phone" in vals:
                vals_to_base["full_phone"] = vals["full_phone"]
            if "country_id" in vals:
                vals_to_base["country_id"] = vals["country_id"]
            res = super().write(vals_to_base)
            if vals.get("new_phone") or vals.get("country_id"):
                for rec in self:
                    if rec.full_phone and rec.country_id:
                        for phone in rec.full_phone:
                            if not phone.country_id:
                                phone.country_id = rec.country_id.id
            trigger_vals_safe = {
                k: v for k, v in trigger_vals.items()
                if getattr(self._fields.get(k), "column_type", None)
            }
            if "new_phone" in trigger_vals_safe:
                trigger_vals_safe["new_phone"] = False
            trigger_vals_relation = {k: v for k, v in trigger_vals.items() if k not in trigger_vals_safe}
            if trigger_vals_safe:
                self._write(trigger_vals_safe)
            if trigger_vals_relation:
                for fname, value in trigger_vals_relation.items():
                    self._fields[fname].write(self, value)
            return res
        if any(rec._has_active_6033_distribution_lines() and rec.nominated_salesperson_id for rec in self):
            vals = dict(vals, assigned_via_wing_distribution=True)
        res = super().write(vals)
        # Clear field after normal write
        if vals.get("new_phone"):
            self._write({"new_phone": False})
        if vals.get("new_phone") or vals.get("country_id"):
            for rec in self:
                if rec.full_phone and rec.country_id:
                    for phone in rec.full_phone:
                        if not phone.country_id:
                            phone.country_id = rec.country_id.id
        return res

    def action_add_phone_and_save(self):
        """Action for the 'Add/Save' button next to the phone field."""
        self.ensure_one()
        self.write({})
        return True
