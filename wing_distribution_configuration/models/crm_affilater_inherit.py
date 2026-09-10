# -*- coding: utf-8 -*-
# Wing Distribution: Affiliate (Referral) – same algorithm as website/call center reception, no SMS for testing.
# Only in wing_distribution_configuration; do not modify crm_custom_menu.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


def _norm_phone(val):
    if not val or not str(val).strip():
        return None
    p = str(val).strip()
    if p.startswith("+251"):
        p = p[4:]
    elif p.startswith("251"):
        p = p[3:]
    if p.startswith("0"):
        p = p[1:]
    return p if p and len(p) >= 9 else None


def _has_phone_in_vals_affiliate(vals):
    if _norm_phone(vals.get("phone_no")):
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


def _is_duplicate_before_create(env, raw_phone):
    """
    Pre-create duplicate detection so existing customers do NOT consume
    distribution slots.

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

    e164 = f"+{digits}" if raw.startswith("+") else None
    tail = digits[-10:] if len(digits) >= 10 else (digits[-9:] if len(digits) >= 9 else None)

    # 1) temer.phone (any country)
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

    # 2) temer.lead / old crm.lead (best-effort)
    try:
        if "wing.duplicate.phone.mixin" in env:
            candidate = e164 or raw
            sp, _sup, _msg = env["wing.duplicate.phone.mixin"].sudo()._wing_find_existing_temer_and_old_crm_only(candidate)
            if sp:
                return True
    except Exception:
        pass

    return False


class CrmAffilaterWingDistribution(models.Model):
    _name = "crm.affilater"
    _inherit = ["crm.affilater", "wing.duplicate.phone.mixin", "wing.sales.team.sms.mixin"]
    wing_duplicate_popup_pending = fields.Boolean(
        string="Duplicate Popup Pending",
        default=False,
        copy=False,
        help="Internal flag: show duplicate popup once after detecting existing customer.",
    )

    @api.onchange("phone_no", "full_phone")
    def _onchange_phone_duplicate_check(self):
        if not self.phone_no and not self.full_phone:
            return
        raw = (self.phone_no or "").strip() if self.phone_no else ""
        if not raw and self.full_phone:
            raw = (self.full_phone[0].name or "").strip()
        if not raw:
            return
        
        msg = self._get_duplicate_phone_message(raw)
        if msg:
            self.phone_number_message = msg
            return {
                "warning": {
                    "title": _("Already registered"),
                    "message": msg,
                }
            }

    def _send_sms_for_duplicate(self):
        """Send SMS for duplicate phone numbers automatically using standard Wing logic."""
        self.ensure_one()
        if not self.existing_salesperson_id:
            _logger.info("Wing Affiliate: skipping SMS for duplicate because no existing_salesperson_id for id=%s.", self.id)
            return

        _logger.info("=== AUTOMATIC SMS FOR DUPLICATE PHONE (AFFILIATE) id=%s ===", self.id)
        # Use the unified background sender for existing customers.
        self.env["wing.existing.customer.sms"].send_for_record_in_background(
            self._name, self.id, "Referral"
        )

    def _create_temer_lead_automatically(self):
        """Wing: Base clears phone_no before calling; run full lead+SMS using full_phone."""
        self.ensure_one()
        if getattr(self, "phone_number_message", None) and (self.phone_number_message or "").strip():
            return
        if getattr(self, "existing_salesperson_id", None) and self.existing_salesperson_id:
            return
        if getattr(self, "existing_temer_lead_id", None) and self.existing_temer_lead_id:
            return
        raw_phone = (self.phone_no or "").strip() if self.phone_no else None
        if not raw_phone and self.full_phone:
            raw_phone = (self.full_phone[0].name or "").strip()
        if not raw_phone:
            return super()._create_temer_lead_automatically()
        # Hard guard: check by phone digits regardless of country_id.
        if _is_duplicate_before_create(self.env, raw_phone):
            _logger.info(
                "Wing Distribution (Affiliate): phone already exists, skipping new lead for id=%s.", self.id
            )
            try:
                self._wing_backfill_duplicate_owner_from_phone(raw_phone)
            except Exception:
                pass
            return
        country_code = (self.country_id.code if self.country_id else None) or "ET"
        if not isinstance(country_code, str):
            country_code = "ET"
        normalized_phone = self._normalize_phone_number(raw_phone, country_code) or raw_phone
        clean_phone = raw_phone.strip() if raw_phone else ""
        clean_phone = clean_phone.replace(" ", "").replace("-", "").replace("+", "")
        if clean_phone.startswith("251"):
            clean_phone = clean_phone[3:]
        if clean_phone.startswith("0"):
            clean_phone = clean_phone[1:]
        if not clean_phone or len(clean_phone) < 9:
            return super()._create_temer_lead_automatically()
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
                    "Wing Distribution (Affiliate): phone %s already in temer.phone; treating as duplicate for id=%s.",
                    formatted_phone,
                    self.id,
                )
                # Use the lead's user_id only if it is a real salesperson (has supervisor mapping).
                # If lead.user_id is the creator (no supervisor), fall back to the mixin lookup.
                lead_user = getattr(lead, "user_id", None)
                existing_salesperson = None
                if lead_user and self._wing_user_has_supervisor(lead_user):
                    existing_salesperson = lead_user
                if not existing_salesperson:
                    sp, _sup, _msg = self._wing_find_existing_temer_and_old_crm_only(formatted_phone)
                    if sp and self._wing_user_has_supervisor(sp):
                        existing_salesperson = sp
                can_send = bool(existing_salesperson and self._wing_user_has_phone(existing_salesperson))
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
                    "phone_number_message": msg,
                    "wing_duplicate_popup_pending": True,
                }
                if existing_salesperson and "existing_salesperson_id" in self._fields:
                    duplicate_vals["existing_salesperson_id"] = existing_salesperson.id
                if existing_salesperson and "existing_temer_lead_id" in self._fields:
                    duplicate_vals["existing_temer_lead_id"] = lead.id
                if existing_salesperson and hasattr(self, "_get_supervisor_for_salesperson"):
                    sup = self._get_supervisor_for_salesperson(existing_salesperson)
                    if sup and "existing_supervisor_id" in self._fields and getattr(
                        sup, "_name", None
                    ) == "property.sales.supervisor":
                        duplicate_vals["existing_supervisor_id"] = sup.id
                self.write(duplicate_vals)
                env = self.env
                model_name, res_id, src = self._name, self.id, "Referral"

                if can_send:
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            self, src
                        )
                        if success:
                            self.write({"state_crm": "sent", "wing_sms_sent": True})
                            return
                        _logger.warning(
                            "Wing Distribution (Affiliate): existing-customer SMS failed for id=%s: %s",
                            self.id,
                            err_msg or "unknown",
                        )
                    except Exception:
                        _logger.exception(
                            "Wing Distribution (Affiliate): error sending existing-customer SMS immediately for id=%s.",
                            self.id,
                        )

                    def _schedule_sms():
                        env["wing.existing.customer.sms"].send_for_record_in_background(model_name, res_id, src)

                    env.cr.postcommit.add(_schedule_sms)
                return
        source_id = self.source_id.id or self.env["utm.source"].search([("name", "=", "Referral")], limit=1).id
        lead_values = {
            "name": self.name or f"Lead from {self.customer_name.strip()}",
            "customer_name": self.customer_name.strip(),
            "phone_no": clean_phone,
            "site_ids": [(6, 0, self.site_ids.ids)],
            "country_id": self.country_id.id,
            "source_ids": source_id,
            "user_id": self.nominated_salesperson_id.id,
            "state": "prospect",
            "from_affilater": True,
            "is_duplicate_phone": False,
        }
        lead = False
        try:
            lead = self.env["temer.lead"].sudo().with_context(
                mail_create_nosubscribe=True, mail_create_nolog=True, tracking_disable=True
            ).create(lead_values)
            _logger.info("Wing Distribution (Affiliate): creating lead and sending SMS for id=%s", self.id)
            sup = self.nominated_supervisor_id or self._get_supervisor_for_salesperson(self.nominated_salesperson_id)
            self.write({"nominated_supervisor_id": sup.id if sup else False})
            sales_ok, err_msg = self._send_sales_team_sms_from_record(
                source="Referral",
                is_existing=False,
                lead=lead,
                customer_phone_override=normalized_phone,
            )
            if not sales_ok:
                _logger.warning(
                    "Wing Distribution (Affiliate): SMS reported failure for id=%s (%s). Lead kept; not blocking.",
                    self.id,
                    err_msg or "unknown",
                )
            self.write({
                "assigned_salesperson_id": self.nominated_salesperson_id.id,
                "assigned_wing_id": self.nominated_wing_id.id if self.nominated_wing_id else False,
                "assigned_supervisor_id": sup.id if sup else False,
                "state_crm": "sent",
            })
        except Exception as e:
            _logger.error("Wing Distribution (Affiliate): error creating lead/SMS: %s", str(e))
            try:
                if lead:
                    lead.unlink()
            except Exception:
                _logger.exception("Wing Distribution (Affiliate): failed to cleanup lead after error.")
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

    def _has_active_affiliate_distribution_lines(self):
        return self._has_active_distribution_lines("affiliate")

    def _get_active_affiliate_users(self):
        """Return users from active Affiliate distribution lines. Uses mixin so no Reception record needed."""
        return self._get_active_distribution_users("affiliate")

    def _get_next_user_by_weighted_team(self, type_code="affiliate"):
        """Use mixin (same algorithm as Reception); works without any Reception record."""
        return super()._get_next_user_by_weighted_team(type_code)

    def _get_next_available_rr_user_and_config(self):
        # Important: when phone is duplicate, skip distribution to avoid serving a line.
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (Affiliate): skipping distribution due to duplicate-phone precheck (context flag)."
            )
            return (False, False)
        # Extra safety: if this record's phone is already registered, do not serve any line.
        raw = ""
        if getattr(self, "phone_no", None):
            raw = (self.phone_no or "").strip()
        if not raw and getattr(self, "full_phone", None) and self.full_phone:
            raw = (self.full_phone[0].name or "").strip()
        if raw and _is_duplicate_before_create(self.env, raw):
            _logger.info(
                "Wing Distribution (Affiliate): runtime duplicate detected for %s, skipping distribution.",
                raw,
            )
            return (False, False)
        if self._has_active_affiliate_distribution_lines():
            _logger.info("Wing Distribution (Affiliate): using weighted assignment (affiliate type active).")
            return self._get_next_user_by_weighted_team("affiliate")
        _logger.info("Wing Distribution (Affiliate): no config or no active users in wing config; not nominating.")
        return (False, False)

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        return self._wing_find_existing_temer_and_old_crm_only(full_phone_number)[2]

    def _get_existing_salesperson_info(self, full_phone_number):
        sp, sup, _ = self._wing_find_existing_temer_and_old_crm_only(full_phone_number)
        return (sp, sup, False) if sp else (None, None, False)

    def _send_sms_to_existing_sales_team(self):
        """Use wing.existing.customer.sms model only (no crm_custom_menu logic). 1 or 2 SMS."""
        wiz = self.env["wing.existing.customer.sms"].create({})
        return wiz.send_for_record(self, "Referral")

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
        _logger.info("Wing Distribution (Affiliate): crm.affilater create called, count=%s.", len(vals_list))
        # Require phone number before save - block create completely if no phone
        for vals in vals_list:
            if not _has_phone_in_vals_affiliate(vals):
                raise UserError(_("Please insert a phone number."))
        # Validation: block save when no active wing config (show error, do not use old algo)
        if not self._has_active_affiliate_distribution_lines():
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Affiliate (Referral). "
                    "Please add Affiliate distribution type with active users in Wing Distribution, or activate existing lines. Lead not created."
                )
            )
        users = self._get_active_affiliate_users()
        if not users:
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Affiliate (Referral). "
                    "Please add users to Affiliate distribution lines or activate them. Lead not created."
                )
            )
        # Base crm.affilater uses create(self, vals); call per record.
        # Create one-by-one so duplicates can bypass distribution and never "serve" a slot.
        records = self.env["crm.affilater"]
        for vals in vals_list:
            raw = (vals.get("phone_no") or "").strip() if vals.get("phone_no") else ""
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
            records |= super(CrmAffilaterWingDistribution, self.with_context(ctx)).create(vals)
        for rec in records:
            try:
                raw = (rec.phone_no or "").strip() if getattr(rec, "phone_no", None) else ""
                if not raw and getattr(rec, "full_phone", None) and rec.full_phone:
                    raw = (rec.full_phone[0].name or "").strip()
                if raw:
                    rec._wing_backfill_duplicate_owner_from_phone(raw)
            except Exception:
                pass
            is_duplicate = bool(
                getattr(rec, "existing_salesperson_id", None) and rec.existing_salesperson_id
            ) or bool(getattr(rec, "phone_number_message", None) and (rec.phone_number_message or "").strip())
            if is_duplicate:
                existing_salesperson = getattr(rec, "existing_salesperson_id", None) and rec.existing_salesperson_id
                msg = rec._wing_duplicate_message_for_salesperson(existing_salesperson) if existing_salesperson else _(
                    "Customer is already registered."
                )
                rec.write({
                    "nominated_salesperson_id": False,
                    "nominated_wing_id": False,
                    "nominated_supervisor_id": False,
                    "assigned_salesperson_id": False,
                    "assigned_wing_id": False,
                    "assigned_supervisor_id": False,
                    "state_crm": "sent",
                    "wing_duplicate_popup_pending": True,
                    "wing_sms_sent": False,
                    "phone_number_message": msg,
                })
                model_name, res_id, src = rec._name, rec.id, "Referral"
                env = rec.env

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(
                        model_name, res_id, src
                    )

                env.cr.postcommit.add(_schedule_sms)
                continue
            if rec._has_active_affiliate_distribution_lines() and rec.nominated_salesperson_id:
                super(CrmAffilaterWingDistribution, rec).write({
                    "assigned_salesperson_id": rec.nominated_salesperson_id.id,
                    "assigned_via_wing_distribution": True,
                })
                _logger.info(
                    "Wing Distribution (Affiliate): id=%s assigned_salesperson_id=%s.",
                    rec.id,
                    rec.nominated_salesperson_id.name,
                )
        return records

    _WRITE_TRIGGER_KEYS = {"customer_name", "site_ids", "phone_no", "full_phone"}

    def write(self, vals):
        # Assignment only on create; on update do not run algorithm and do not set "served"
        if not vals:
            return True
        # On duplicate we allow save; form shows existing salesperson; popup "Customer is already registered" (JS)
        # Block save when draft would have no phone after this write
        trigger_in_vals = self._WRITE_TRIGGER_KEYS & set(vals)
        if trigger_in_vals:
            for rec in self:
                if getattr(rec, "state_crm", None) != "draft":
                    continue
                will_have_phone = bool(_norm_phone(vals.get("phone_no")))
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
                    has_existing = bool(rec.full_phone) or bool(_norm_phone(getattr(rec, "phone_no", None)))
                    if not has_existing:
                        raise UserError(_("Please insert a phone number."))
        assignment_keys = {"nominated_salesperson_id", "assigned_salesperson_id"}
        if assignment_keys & set(vals):
            if any(
                rec._has_active_affiliate_distribution_lines() and rec.nominated_salesperson_id
                for rec in self
            ):
                vals = dict(vals, assigned_via_wing_distribution=True)
            return super().write(vals)
        trigger_in_vals = self._WRITE_TRIGGER_KEYS & set(vals)
        preserve = trigger_in_vals and any(
            rec._has_active_affiliate_distribution_lines()
            and (rec.nominated_salesperson_id or rec.assigned_salesperson_id)
            for rec in self
        )
        if preserve:
            other_vals = {k: v for k, v in vals.items() if k not in self._WRITE_TRIGGER_KEYS}
            trigger_vals = {k: vals[k] for k in trigger_in_vals}
            vals_to_base = dict(other_vals)
            if "phone_no" in vals:
                vals_to_base["phone_no"] = vals["phone_no"]
            if "full_phone" in vals:
                vals_to_base["full_phone"] = vals["full_phone"]
            res = super().write(vals_to_base)
            trigger_vals_safe = {
                k: v for k, v in trigger_vals.items()
                if getattr(self._fields.get(k), "column_type", None)
            }
            if "phone_no" in trigger_vals_safe:
                trigger_vals_safe["phone_no"] = ""
            trigger_vals_relation = {k: v for k, v in trigger_vals.items() if k not in trigger_vals_safe}
            if trigger_vals_safe:
                self._write(trigger_vals_safe)
            if trigger_vals_relation:
                for fname, value in trigger_vals_relation.items():
                    self._fields[fname].write(self, value)
            
            # Clear field after write
            if "phone_no" in vals:
                self._write({"phone_no": ""})
            return res
        if any(rec._has_active_affiliate_distribution_lines() and rec.nominated_salesperson_id for rec in self):
            vals = dict(vals, assigned_via_wing_distribution=True)
        res = super().write(vals)
        # Clear field after normal write
        if vals.get("phone_no"):
            self._write({"phone_no": ""})
        return res

    def action_add_phone_and_save(self):
        """Action for the 'Add/Save' button next to the phone field."""
        self.ensure_one()
        self.write({})
        return True
