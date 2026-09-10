# -*- coding: utf-8 -*-
# Single method for salesperson + supervisor SMS: one message or two (if same person = one SMS, else two).
# Also provides wing distribution assignment helpers so Website/CallCenter/Affiliate work without any Reception record.

import logging
import random

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

# Source name for wing config lookup by distribution type code (walk_in, website, 6033, affiliate)
WING_DISTRIBUTION_SOURCE_BY_CODE = {"walk_in": "Walk In", "website": "Website", "6033": "6033", "affiliate": "Referral"}


class WingSalesTeamSmsMixin(models.AbstractModel):
    """
    Mixin: one method to build and send SMS to salesperson and supervisor.
    - If salesperson == supervisor: send one SMS (salesperson message).
    - If different: send two SMS (salesperson message + supervisor message).
    """

    _name = "wing.sales.team.sms.mixin"
    _description = "Wing: unified sales team SMS (salesperson + supervisor, one or two messages)"

    def _send_sms(self, mobile_number, message):
        """
        Single gateway for all SMS: calls wing_sms.send_sms_afromessage.
        All 4 CRMs use this (inherited from mixin); change token/API only in wing_sms.py.
        """
        from .wing_sms import send_sms_afromessage
        return send_sms_afromessage(mobile_number, message, env=self.env)

    def _send_email_notification(self, email_address, message, recipient_name=""):
        """Send a plain-text email notification via Odoo's mail system."""
        try:
            subject = _("New Lead Notification – Temer Properties")
            body_html = "<pre>%s</pre>" % message
            self.env["mail.mail"].sudo().create({
                "subject": subject,
                "body_html": body_html,
                "email_to": email_address,
                "auto_delete": True,
            }).send()
            _logger.info(
                "Wing Distribution: email notification sent to %s (%s).",
                recipient_name or email_address,
                email_address,
            )
            return True, "Email sent successfully"
        except Exception as e:
            _logger.exception("Wing Distribution: email notification failed for %s: %s", email_address, e)
            return False, str(e)

    def _send_notification(self, mobile_number, email_address, message, recipient_name=""):
        """
        Send SMS if mobile_number is available; otherwise fall back to email.
        Returns (success, error_message).
        """
        if mobile_number and str(mobile_number).strip():
            return self._send_sms(mobile_number, message)
        if email_address and str(email_address).strip():
            _logger.info(
                "Wing Distribution: no phone for %s, falling back to email (%s).",
                recipient_name or "recipient",
                email_address,
            )
            return self._send_email_notification(email_address, message, recipient_name)
        return False, _("No phone or email available for %s.") % (recipient_name or "recipient")

    def _wing_is_existing_customer(self):
        """
        True if this record is an EXISTING customer, so wing distribution
        MUST NOT consume a slot (no 'served' status update).
        """
        self.ensure_one()

        # 1) Base duplicate flags filled by CRM logic
        if getattr(self, "existing_salesperson_id", False):
            return True
        if getattr(self, "existing_temer_lead_id", False):
            return True
        msg = (getattr(self, "phone_number_message", "") or "").strip()
        if msg:
            return True

        # 2) Extra guard: phone already exists in temer.phone => also treat as existing
        try:
            # IMPORTANT: env is a mapping; use 'in' instead of .get()
            if "temer.phone" in self.env:
                Phone = self.env["temer.phone"].sudo()
                # Get phone from record
                if hasattr(self, "_get_customer_phone_from_record"):
                    raw = (self._get_customer_phone_from_record() or "").strip()
                else:
                    raw = (
                        getattr(self, "phone_no", None)
                        or getattr(self, "new_phone", None)
                        or ""
                    ).strip()
                    if not raw and getattr(self, "full_phone", None) and self.full_phone:
                        raw = (self.full_phone[0].name or "").strip()
                if raw:
                    e164 = self._wing_format_e164(raw)
                    digits = "".join(ch for ch in raw if ch.isdigit())
                    tail = digits[-10:] if len(digits) >= 10 else (digits[-9:] if len(digits) >= 9 else "")
                    # Always include tail fallback so Ethiopia/non-ET and formats still match.
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
        except Exception:
            # If anything goes wrong, fall back to base flags only
            pass

        return False

    def _wing_format_e164(self, raw):
        """
        Best-effort format customer phone to +<country_code><national_number>.
        Uses record country_id.phone_code when available. If raw already starts with '+', return normalized '+digits'.
        """
        if not raw or not str(raw).strip():
            return None
        s = str(raw).strip()
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            return None
        # If user already provided +..., trust it (but normalize to +digits).
        if s.startswith("+"):
            return f"+{digits}"
        country = getattr(self, "country_id", None)
        code = str(getattr(country, "phone_code", "") or "").strip() if country else ""
        if not code:
            return None
        # Strip leading country code if user typed it, and strip trunk 0.
        if digits.startswith(code):
            digits = digits[len(code):]
        if digits.startswith("0"):
            digits = digits[1:]
        if not digits:
            return None
        return f"+{code}{digits}"

    def _send_sales_team_sms(
        self,
        salesperson,
        supervisor,
        customer_name,
        customer_phone,
        source,
        is_existing=False,
        lead=None,
    ):
   
        self.ensure_one()
        if not salesperson or not salesperson.partner_id:
            return False, _("No salesperson or contact.")
        sales_mobile, sales_email = self._wing_get_user_sms_target_and_email(salesperson)
        if not sales_mobile and not sales_email:
            if is_existing:
                return False, _(
                    "Customer already registered but the assigned salesperson does not have a phone number in the system."
                )
            return False, _("Salesperson has no mobile or phone number.")
        sales_name = salesperson.name or "Sales Person"
        src = (source or "").strip() or "Walk In"
        phone_display = (customer_phone or "").strip() or ""
        cust_name = (customer_name or "").strip() or phone_display or "Customer"

        def _resolve_supervisor_user(sup):
            """
            Normalize supervisor to a `res.users` record (or None).

            Different databases may store supervisor as:
            - `res.users`
            - `property.sales.supervisor` (with field `name` = res.users)
            - any custom mapping model (with `user_id`/`name` pointing to res.users)
            """
            if not sup:
                return None
            # Already a user
            if getattr(sup, "_name", None) == "res.users":
                return sup
            # Common case: property.sales.supervisor.name is a res.users record
            if getattr(sup, "name", None) and hasattr(sup.name, "_name") and sup.name._name == "res.users":
                return sup.name
            # Some mappings use user_id
            if getattr(sup, "user_id", None) and hasattr(sup.user_id, "_name") and sup.user_id._name == "res.users":
                return sup.user_id
            return None

        supervisor_user = _resolve_supervisor_user(supervisor)
        same_user = bool(supervisor_user and salesperson and supervisor_user.id == salesperson.id)

        if is_existing:
            sales_msg = _(
                "Hi %(sales)s, Customer: %(cust)s (%(phone)s) came via %(source)s. Please follow up."
            ) % {
                "sales": sales_name,
                "cust": cust_name,
                "phone": phone_display,
                "source": src,
            }
            supervisor_msg = None
            sup_mobile = None
            sup_email = None
            if not same_user and supervisor_user:
                sup_mobile, sup_email = self._wing_get_user_sms_target_and_email(supervisor_user)
                if sup_mobile or sup_email:
                    supervisor_msg = _(
                        "Hi %(super)s, salesperson under your supervision %(sales)s's customer contacted us via %(source)s. Please follow up."
                    ) % {
                        "super": supervisor_user.name or "Supervisor",
                        "sales": sales_name,
                        "source": src,
                    }
        else:
            sales_msg = _(
                "Hi %(sales)s, New lead from %(source)s: Customer %(cust)s (%(phone)s). Please follow up."
            ) % {
                "sales": sales_name,
                "source": src,
                "cust": cust_name,
                "phone": phone_display,
            }
            supervisor_msg = None
            sup_mobile = None
            sup_email = None
            if not same_user and supervisor_user:
                sup_mobile, sup_email = self._wing_get_user_sms_target_and_email(supervisor_user)
                if sup_mobile or sup_email:
                    supervisor_msg = _(
                        "Hi %(super)s, salesperson under your supervision %(sales)s got a new lead from %(source)s. Please follow up."
                    ) % {
                        "super": supervisor_user.name or "Supervisor",
                        "sales": sales_name,
                        "source": src,
                    }

        ok, err = self._send_notification(sales_mobile, sales_email, sales_msg, salesperson.name or "salesperson")
        if not ok:
            return False, err or _("Failed to send notification to salesperson.")
        if hasattr(lead, "message_post") and lead:
            try:
                lead.message_post(
                    body=_("SMS notification sent to salesperson: %s") % sales_name,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
            except Exception:
                pass
        # If we have a different supervisor and a contact, send the second notification.
        # Treat failure as a WARNING (do not block the workflow).
        if supervisor_msg and (sup_mobile or sup_email):
            ok2, err2 = self._send_notification(sup_mobile, sup_email, supervisor_msg, supervisor_user.name or "supervisor")
            if not ok2:
                return True, _(
                    "Notification sent to salesperson, but failed to send to supervisor (%(reason)s)."
                ) % {"reason": (err2 or _("unknown reason"))}
            if hasattr(lead, "message_post") and lead:
                try:
                    lead.message_post(
                        body=_("SMS notification sent to supervisor: %s") % (supervisor_user.name or "Supervisor"),
                        message_type="comment",
                        subtype_xmlid="mail.mt_comment",
                    )
                except Exception:
                    pass

        return True, None

    def _get_customer_phone_from_record(self, override=None):
        """Get customer phone from current record (works for reception, website, callcenter, affilater)."""
        phone = None
        if override and str(override).strip():
            phone = str(override).strip()
        if getattr(self, "phone_no", None) and str(self.phone_no).strip():
            phone = str(self.phone_no).strip()
            if hasattr(self, "_normalize_phone_number") and getattr(self, "country_id", None):
                cc = self.country_id.code if self.country_id else "ET"
                if not isinstance(cc, str):
                    cc = "ET"
                phone = self._normalize_phone_number(phone, cc) or phone
        elif getattr(self, "new_phone", None) and str(self.new_phone).strip():
            if not phone:
                phone = str(self.new_phone).strip()
        if not phone and getattr(self, "full_phone", None) and self.full_phone:
            phone = (self.full_phone[0].name or "").strip()
        # Normalize to local digits when model provides helper
        if phone and hasattr(self, "_normalize_phone"):
            phone = self._normalize_phone(phone) or phone
        phone = (phone or "").strip()
        # For display/SMS, prefer full international form +<country_code><local>
        try:
            country = getattr(self, "country_id", None)
            if country and getattr(country, "phone_code", None) and phone:
                local = phone
                # strip any leading '+' and country code if present
                p2 = local.replace(" ", "").replace("-", "").replace("+", "")
                code = str(country.phone_code)
                if p2.startswith(code):
                    p2 = p2[len(code):]
                if p2.startswith("0"):
                    p2 = p2[1:]
                if p2:
                    return f"+{code}{p2}"
        except Exception:
            pass
        return phone

    def _send_sales_team_sms_from_record(
        self,
        source,
        is_existing=False,
        lead=None,
        customer_phone_override=None,
        salesperson_override=None,
        supervisor_override=None,
    ):
       
        self.ensure_one()
        if is_existing:
            salesperson = salesperson_override or (getattr(self, "existing_salesperson_id", None) and self.existing_salesperson_id)
            if not salesperson:
                return False, _("No existing salesperson found for this phone number.")
            supervisor = supervisor_override or (getattr(self, "existing_supervisor_id", None) and self.existing_supervisor_id)
        else:
            salesperson = salesperson_override or (getattr(self, "nominated_salesperson_id", None) and self.nominated_salesperson_id)
            if not salesperson:
                return False, _("No salesperson to notify.")
            supervisor = supervisor_override or (getattr(self, "nominated_supervisor_id", None) and self.nominated_supervisor_id)
        if not supervisor and salesperson and hasattr(self, "_get_supervisor_for_salesperson"):
            supervisor = self._get_supervisor_for_salesperson(salesperson)
        customer_name = (getattr(self, "customer_name", None) or "").strip() or "Customer"
        customer_phone = self._get_customer_phone_from_record(customer_phone_override)
        return self._send_sales_team_sms(
            salesperson=salesperson,
            supervisor=supervisor,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source=source,
            is_existing=is_existing,
            lead=lead,
        )

    # -------------------------------------------------------------------------
    # Wing distribution assignment (shared by Reception, Website, Call Center, Affiliate)
    # So Website/CallCenter/Affiliate work even when no Reception record exists yet.
    # -------------------------------------------------------------------------

    def _has_active_distribution_lines(self, type_code):
        """True if there is at least one active distribution line for this type."""
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

    def _get_active_distribution_users(self, type_code):
        """Return all users in active distribution lines for this type."""
        dist_type = self.env["wing.distribution.type"].sudo().search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = self.env["wing.distribution.type"].sudo().search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            return self.env["res.users"]
        lines = self.env["wing.distribution.line"].sudo().search(
            [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
        )
        return lines.mapped("user_id")

    def _get_wing_config_for_source(self, wing, source_name):
        """Get property.wing.config for given wing and lead source (e.g. Walk In, Website, 6033)."""
        WingConfig = self.env["property.wing.config"]
        if wing:
            config = WingConfig.search(
                [("source_id.name", "=", source_name), ("wing_id", "=", wing.id)],
                limit=1,
            )
            if config:
                return config
        return WingConfig.search([("source_id.name", "=", source_name)], limit=1)

    def _wing_get_supervisor_for_salesperson(self, salesperson):
        """
        Resolve the supervisor for a salesperson user (or return False).

        Tries, in order:
        - model-specific `_get_supervisor_for_salesperson` if available
        - property.sales.supervisor (name = res.users)
        - property.salesperson.mapping (user_id -> supervisor_id)
        """
        if not salesperson:
            return False
        sup = False
        try:
            if hasattr(self, "_get_supervisor_for_salesperson"):
                sup = self._get_supervisor_for_salesperson(salesperson)
        except Exception:
            sup = False
        if not sup and "property.sales.supervisor" in self.env:
            sup = self.env["property.sales.supervisor"].sudo().search(
                [("name", "=", salesperson.id)], limit=1
            )
        if not sup and "property.salesperson.mapping" in self.env:
            mapping = self.env["property.salesperson.mapping"].sudo().search(
                [("user_id", "=", salesperson.id)], limit=1
            )
            sup = mapping.supervisor_id if mapping else False
        return sup

    def _wing_user_has_phone(self, user):
        """True if user (or linked partner) has any phone/mobile value OR an email/login (used as fallback contact)."""
        if not user:
            return False
        for val in (getattr(user, "phone", None), getattr(user, "mobile", None)):
            if val and str(val).strip():
                return True
        partner = getattr(user, "partner_id", None)
        if partner:
            for val in (getattr(partner, "phone", None), getattr(partner, "mobile", None)):
                if val and str(val).strip():
                    return True
            if getattr(partner, "email", None) and str(partner.email).strip():
                return True
        # user.login is the "Email Address" field shown on the user form in Odoo
        for val in (getattr(user, "email", None), getattr(user, "login", None)):
            if val and str(val).strip():
                return True
        return False

    def _wing_get_user_sms_target_and_email(self, user):
        """
        Return (sms_number, email) for a user.

        Handles the common case where a phone number is stored in the Email Address
        field (e.g. '0970414609' in email) — treated as an SMS number, not email.

        Priority:
        1. mobile/phone fields → SMS number
        2. phone/mobile field containing '@' → email
        3. email field containing digits only (no '@') → SMS number
        4. email field containing '@' → real email fallback
        """
        if not user:
            return None, None
        partner = getattr(user, "partner_id", None)
        sms_number = None
        email = None

        # Collect all phone/mobile field candidates
        candidates = []
        if partner:
            for val in (getattr(partner, "mobile", None), getattr(partner, "phone", None)):
                if val and str(val).strip():
                    candidates.append(str(val).strip())
        for val in (getattr(user, "mobile", None), getattr(user, "phone", None)):
            if val and str(val).strip():
                candidates.append(str(val).strip())

        for c in candidates:
            if "@" in c:
                if not email:
                    email = c
            else:
                if not sms_number:
                    sms_number = c

        # Check the email field — it may contain a phone number instead of a real email
        email_field_val = None
        if partner and getattr(partner, "email", None) and str(partner.email).strip():
            email_field_val = str(partner.email).strip()
        elif getattr(user, "email", None) and str(user.email).strip():
            email_field_val = str(user.email).strip()
        elif getattr(user, "login", None) and str(user.login).strip():
            # user.login is the "Email Address" field on the Odoo user form
            email_field_val = str(user.login).strip()

        if email_field_val:
            if "@" in email_field_val:
                # Real email address
                if not email:
                    email = email_field_val
            else:
                # Phone number stored in the email field — use as SMS target
                if not sms_number:
                    sms_number = email_field_val

        return sms_number, email

    def _wing_duplicate_message_for_salesperson(self, salesperson):
        """
        Message shown for duplicate customers.
        If the assigned salesperson has no phone/mobile, show a clearer warning.
        """
        if salesperson and not self._wing_user_has_phone(salesperson):
            return _(
                "Customer already registered but the assigned salesperson does not have a phone number in the system."
            )
        return _("Customer is already registered.")

    def _wing_user_has_supervisor(self, user):
        """True if user exists, is active (if applicable), has phone/email, and has a supervisor mapping."""
        if not user:
            return False
        if hasattr(user, "active") and not user.active:
            return False
        if not self._wing_user_has_phone(user):
            return False
        sup = self._wing_get_supervisor_for_salesperson(user)
        if not sup:
            return False
        # Resolve supervisor to res.users so we can check their contact info
        sup_user = None
        if getattr(sup, "_name", None) == "res.users":
            sup_user = sup
        elif getattr(sup, "name", None) and getattr(sup.name, "_name", None) == "res.users":
            sup_user = sup.name
        elif getattr(sup, "user_id", None) and getattr(sup.user_id, "_name", None) == "res.users":
            sup_user = sup.user_id
        # If we can resolve to a user, check they have a contact; otherwise trust the mapping exists
        if sup_user:
            return self._wing_user_has_phone(sup_user)
        return True

    def _wing_release_distribution_slot(self, type_code="walk_in"):
        """If distribution assignment fails (SMS error), make the previously used line available again.

        This ensures that a line isn't left in a "served/reserved" state when the SMS was not sent.
        """
        try:
            dist_type = self.env["wing.distribution.type"].sudo().search(
                [("code", "=", type_code)],
                limit=1,
            )
            if not dist_type:
                return
            user = getattr(self, "nominated_salesperson_id", None) or getattr(self, "assigned_salesperson_id", None)
            if not user:
                return
            lines = self.env["wing.distribution.line"].sudo().search(
                [
                    ("user_id", "=", user.id),
                    ("distribution_type_ids", "in", [dist_type.id]),
                    ("status", "=", "served"),
                ]
            )
            if lines:
                lines.sudo().write({"status": False})
                # Also reset the TeamState status for the wings of these lines
                # so the team isn't blocked until the round finishes.
                wing_ids = lines.mapped("wing_id").ids
                if wing_ids:
                    self.env["wing.distribution.team.state"].sudo().search([
                        ("distribution_type_id", "=", dist_type.id),
                        ("wing_id", "in", wing_ids),
                        ("status", "=", "served")
                    ]).write({"status": False})
        except Exception:
            # Best-effort only
            pass

    def _finish_wing_distribution_round(self, round_record, dist_type, all_lines):
        """
        Mark round as served.

        IMPORTANT UX / Audit behavior:
        - We DO NOT immediately reset line.status or round_id here.
          This keeps the last assignment visible in the Wing Distribution list
          (status="served", round_id=Round N) until the next lead arrives.
        - Lines are reset/joined for the next round when a new round starts.
        """
        round_record.sudo().write({"status": "served", "date_served": fields.Datetime.now()})
        self.env["wing.distribution.team.state"].sudo().search(
            [("distribution_type_id", "=", dist_type.id)]
        ).write({"status": False})
        _logger.info("Wing Distribution: round %s marked served, wing states reset.", round_record.name)

    def _pick_next_state_by_sequence(self, states, dist_type):
        Param = self.env["ir.config_parameter"].sudo()
        if not states:
            return False
        sorted_states = sorted(states, key=lambda s: s.wing_id.id)
        key = "wing_distribution.last_wing_%s" % dist_type.id
        last_wing_id = int(Param.get_param(key, default="0") or 0)
        if last_wing_id:
            # Try exact match first
            for idx, state in enumerate(sorted_states):
                if state.wing_id.id == last_wing_id:
                    next_state = sorted_states[(idx + 1) % len(sorted_states)]
                    Param.set_param(key, str(next_state.wing_id.id))
                    return next_state
            # last_wing_id not in current candidates (e.g. that wing has no remaining lines).
            # Pick the first wing whose ID is greater than last_wing_id (wrap around if needed).
            greater = [s for s in sorted_states if s.wing_id.id > last_wing_id]
            next_state = greater[0] if greater else sorted_states[0]
            Param.set_param(key, str(next_state.wing_id.id))
            _logger.info(
                "Wing Distribution: last_wing_id=%s not in candidates %s; picking next by ID: wing=%s.",
                last_wing_id,
                [s.wing_id.id for s in sorted_states],
                next_state.wing_id.name,
            )
            return next_state
        Param.set_param(key, str(sorted_states[0].wing_id.id))
        return sorted_states[0]

    def _log_wing_distribution_state(
        self, dist_type, round_wing_map, state_by_wing, chosen_wing, chosen_state, chosen_line
    ):
        """Log wing distribution state (optional)."""
        header = "Wing Distribution state (type=%s)" % (dist_type.name or "")
        rows = ["Wing | Count | Weight | Wing Status | Lines Served/Total"]
        for wing, wing_lines in round_wing_map.items():
            state = state_by_wing.get(wing.id)
            served_count = len(wing_lines.filtered(lambda l: l.status == "served"))
            total_count = len(wing_lines)
            weight = state.weight if state else 0.0
            wing_status = state.status if state else ""
            rows.append(
                "%s | %s | %.4f | %s | %s/%s"
                % (wing.name or "None", total_count, weight, wing_status or "", served_count, total_count)
            )
        _logger.info("%s\n%s", header, "\n".join(rows))

    def _pick_next_line_for_wing(self, wing_lines, dist_type, wing):
        """
        Deterministically pick the next line for a wing within a round.

        - Order is stable by salesperson name then line id.
        - We remember the last used line per (distribution_type, wing) in ir.config_parameter
          so the next call continues the sequence, even across rounds.
        """
        Param = self.env["ir.config_parameter"].sudo()
        lines = wing_lines
        if not lines:
            return False
        # Stable ordering: by user name (case-insensitive), then line id
        ordered = sorted(
            lines,
            key=lambda l: ((l.user_id.name or "").lower(), l.id or 0),
        )
        key = "wing_distribution.last_line_%s_%s" % (dist_type.id, wing.id)
        last_line_id = int(Param.get_param(key, default="0") or 0)
        chosen = None
        if last_line_id:
            ids = [l.id for l in ordered]
            if last_line_id in ids:
                idx = ids.index(last_line_id)
                chosen = ordered[(idx + 1) % len(ordered)]
        if not chosen:
            chosen = ordered[0]
        Param.set_param(key, str(chosen.id or 0))
        return chosen

    def _get_next_user_by_weighted_team(self, type_code="walk_in"):
        """
        Pick next user by weighted wing.
        type_code: walk_in, website, 6033, affiliate. Works without any CRM record.

        GLOBAL HARD GUARDS:
        - If context says this is a duplicate (existing customer), NEVER serve a slot.
        - If the current record's phone already exists in temer.phone, NEVER serve a slot.
        """
        # 1) Context flag from pre-create duplicate checks (all 4 channels set this)
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info(
                "Wing Distribution (%s): _get_next_user_by_weighted_team skipped due to duplicate-phone context.",
                type_code,
            )
            return False, False

        # 2) Runtime safety: if current record's phone already exists, skip assignment
        try:
            raw = (
                self._get_customer_phone_from_record()
                if hasattr(self, "_get_customer_phone_from_record")
                else None
            )
            raw = (raw or "").strip()
            if raw and "temer.phone" in self.env:
                e164 = self._wing_format_e164(raw)
                digits = "".join(ch for ch in raw if ch.isdigit())
                tail = digits[-10:] if len(digits) >= 10 else (digits[-9:] if len(digits) >= 9 else "")
                if e164:
                    domain = ["|", ("phone", "=", e164), ("phone", "ilike", tail)] if tail else [("phone", "=", e164)]
                else:
                    domain = ["|", ("phone", "=", raw), ("phone", "ilike", tail)] if tail else [("phone", "=", raw)]
                if self.env["temer.phone"].sudo().search_count(domain):
                    _logger.info(
                        "Wing Distribution (%s): runtime duplicate phone %s detected on %s, skipping assignment.",
                        type_code,
                        (e164 or raw),
                        self._name,
                    )
                    return False, False
        except Exception:
            # If anything goes wrong here, do not block the request;
            # the more conservative per-record _wing_is_existing_customer()
            # check later will still protect distribution fairness.
            pass

        # 3) Absolute guard: if *this* record is an existing customer,
        #    do NOT enter the wing distribution algorithm at all.
        #    This keeps all wing.distribution lines and rounds untouched
        #    for existing customers, regardless of where the lead comes from.
        if self:
            try:
                for rec in self:
                    if hasattr(rec, "_wing_is_existing_customer") and rec._wing_is_existing_customer():
                        _logger.info(
                            "Wing Distribution (%s): record %s detected as EXISTING customer, skipping distribution.",
                            type_code,
                            rec._name,
                        )
                        return False, False
            except Exception:
                # If anything goes wrong, fall back to normal flow; the
                # later 'served' gating still prevents unfair consumption.
                pass
        DistributionType = self.env["wing.distribution.type"].sudo()
        DistributionLine = self.env["wing.distribution.line"].sudo()
        TeamState = self.env["wing.distribution.team.state"].sudo()
        DistributionRound = self.env["wing.distribution.round"].sudo()

        dist_type = DistributionType.search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = DistributionType.search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            _logger.info("Wing Distribution: no distribution type found for code=%s.", type_code)
            return False, False

        lines = DistributionLine.search(
            [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
        )
        if not lines:
            _logger.info("Wing Distribution: no active distribution lines.")
            return False, False

        current_round = DistributionRound.search(
            [("distribution_type_id", "=", dist_type.id), ("status", "=", "started")],
            limit=1,
            order="id desc",
        )
        if not current_round:
            # New round starts when there is no active started round.
            # Join lines that are:
            # - not yet in any round, OR were part of a previously served round
            # - and are active participants (status can be False/new/served from previous round display)
            lines_to_join = lines.filtered(
                lambda l: l.status in (False, "new", "served")
                and (not l.round_id or (getattr(l.round_id, "status", None) == "served"))
            )
            if not lines_to_join:
                _logger.info("Wing Distribution: no eligible lines (new/null) for a new round.")
                return False, False
            next_num = (
                DistributionRound.search_count([("distribution_type_id", "=", dist_type.id)]) + 1
            )
            current_round = DistributionRound.sudo().create({
                "name": "Round %d" % next_num,
                "distribution_type_id": dist_type.id,
                "status": "started",
                "date_started": fields.Datetime.now(),
            })
            _logger.info("Wing Distribution: round started %s, lines_joined=%s.", current_round.name, len(lines_to_join))
            lines_to_join.sudo().write({"round_id": current_round.id})
            # Reset for the new round so everyone becomes eligible again
            lines_to_join.sudo().write({"status": False})

        # Fix 1: lines IN the current round but status="new" → reset to NULL so they are visible
        stuck_in_round = lines.filtered(
            lambda l: l.round_id == current_round and l.status == "new"
        )
        if stuck_in_round:
            stuck_in_round.sudo().write({"status": False})
            _logger.info(
                "Wing Distribution: %s line(s) in current round had status='new', reset to NULL.",
                len(stuck_in_round),
            )

        # Fix 2: lines with status=NULL but round_id=NULL → they exist but are not in any round
        # These show as "None" in the UI but are invisible because round_id != current_round
        stuck_no_round = lines.filtered(
            lambda l: not l.round_id and not l.status
        )
        if stuck_no_round:
            stuck_no_round.sudo().write({"round_id": current_round.id})
            _logger.info(
                "Wing Distribution: %s line(s) had no round_id, joined current round %s.",
                len(stuck_no_round),
                current_round.name,
            )

        remaining_lines = lines.filtered(lambda l: l.round_id == current_round and not l.status)
        _logger.info("Wing Distribution: round=%s remaining_lines=%s.", current_round.name, len(remaining_lines))
        if not remaining_lines:
            self._finish_wing_distribution_round(current_round, dist_type, lines)
            _logger.info("Wing Distribution: round %s finished.", current_round.name)
            return self._get_next_user_by_weighted_team(type_code)

        # Skip lines with missing salesperson or missing supervisor (new leads only).
        invalid_lines = remaining_lines.filtered(
            lambda l: not self._wing_user_has_supervisor(l.user_id)
        )
        if invalid_lines:
            # Remove invalid lines from the current round so they join the next round as "New".
            invalid_lines.sudo().write({"status": "new", "round_id": False})
            _logger.warning(
                "Wing Distribution (%s): skipped %s line(s) with missing salesperson/supervisor/phone (moved to next round).",
                type_code,
                len(invalid_lines),
            )
            remaining_lines = lines.filtered(
                lambda l: l.round_id == current_round and not l.status
            )
            if not remaining_lines:
                # All remaining lines were invalid; end the round and abort assignment.
                self._finish_wing_distribution_round(current_round, dist_type, lines)
                _logger.warning(
                    "Wing Distribution (%s): no eligible salespeople with supervisors/phone. Assignment aborted.",
                    type_code,
                )
                return False, False

        wing_remaining_map = {}
        for line in remaining_lines:
            if not line.wing_id:
                continue
            wing_remaining_map.setdefault(line.wing_id, self.env["wing.distribution.line"])
            wing_remaining_map[line.wing_id] |= line

        if not wing_remaining_map:
            _logger.info("Wing Distribution: remaining lines have no wing.")
            return False, False

        total_count = sum(len(wing_lines) for wing_lines in wing_remaining_map.values())
        if not total_count:
            return False, False

        wing_ids = [wing.id for wing in wing_remaining_map.keys()]
        states = TeamState.search(
            [("distribution_type_id", "=", dist_type.id), ("wing_id", "in", wing_ids)]
        )
        state_by_wing = {state.wing_id.id: state for state in states if state.wing_id}

        round_lines = lines.filtered(lambda l: l.round_id == current_round)
        # Always recalculate weights based on current remaining lines.
        # Using stale weights means wings that joined mid-round (or had lines
        # added after the round started) keep weight=0 and never get picked.
        for wing, wing_lines in wing_remaining_map.items():
            state = state_by_wing.get(wing.id)
            if not state:
                state = TeamState.sudo().create({
                    "wing_id": wing.id,
                    "distribution_type_id": dist_type.id,
                })
                state_by_wing[wing.id] = state
            weight = len(wing_lines) / float(total_count)
            state.sudo().write({
                "supervisor_count": len(wing_lines),
                "weight": weight,
                "active": True,
            })

        active_states = [state_by_wing[wing_id] for wing_id in wing_ids if wing_id in state_by_wing]
        candidate_states = [state for state in active_states if not state.status]
        if not candidate_states and active_states:
            TeamState.sudo().browse([state.id for state in active_states]).write({"status": False})
            candidate_states = active_states
        if not candidate_states:
            return False, False

        max_weight = max(state.weight for state in candidate_states)
        top_states = [state for state in candidate_states if state.weight == max_weight]
        chosen_state = self._pick_next_state_by_sequence(top_states, dist_type)
        chosen_wing = None
        for wing in wing_remaining_map.keys():
            if state_by_wing.get(wing.id) and state_by_wing.get(wing.id).id == chosen_state.id:
                chosen_wing = wing
                break
        if not chosen_wing:
            return False, False

        available_lines = wing_remaining_map[chosen_wing]
        if not available_lines:
            chosen_state.sudo().write({"status": "served"})
            return False, False

        # Deterministic per-wing rotation instead of random choice
        chosen_line = self._pick_next_line_for_wing(available_lines, dist_type, chosen_wing)

        # Decide if this call is for a NEW lead or an EXISTING customer.
        is_existing = False
        if self:
            try:
                for rec in self:
                    if hasattr(rec, "_wing_is_existing_customer") and rec._wing_is_existing_customer():
                        is_existing = True
                        break
            except Exception:
                is_existing = False

        if not is_existing:
            # NEW lead: consume a slot and advance the round.
            # We update statuses internally but do NOT use the wording "served"
            # in logs anymore to avoid confusion with existing customers.
            chosen_line.sudo().write({"status": "served"})
            chosen_state.sudo().write({"status": "served"})
            _logger.info(
                "Wing Distribution (type=%s): NEW lead, assigned user=%s wing=%s round=%s.",
                type_code,
                chosen_line.user_id.name,
                chosen_wing.name,
                current_round.name,
            )
        else:
            # EXISTING customer: DO NOT mark served – keep round/weights unchanged
            _logger.info(
                "Wing Distribution (type=%s): EXISTING customer, assigned user=%s wing=%s round=%s (slot NOT consumed).",
                type_code,
                chosen_line.user_id.name,
                chosen_wing.name,
                current_round.name,
            )

        source_name = WING_DISTRIBUTION_SOURCE_BY_CODE.get(type_code, "Walk In")
        config = self._get_wing_config_for_source(chosen_wing, source_name)
        round_wing_map = {}
        for line in lines.filtered(lambda l: l.round_id == current_round):
            if line.wing_id:
                round_wing_map.setdefault(line.wing_id, self.env["wing.distribution.line"])
                round_wing_map[line.wing_id] |= line
        self._log_wing_distribution_state(
            dist_type, round_wing_map, state_by_wing, chosen_wing, chosen_state, chosen_line
        )

        if active_states and all(state.status == "served" for state in active_states):
            TeamState.sudo().browse([state.id for state in active_states]).write({"status": False})
        still_remaining = lines.filtered(lambda l: l.round_id == current_round and not l.status)
        if not still_remaining:
            self._finish_wing_distribution_round(current_round, dist_type, lines)

        return chosen_line.user_id, config
