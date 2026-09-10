# -*- coding: utf-8 -*-

import logging
import random

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


def _is_duplicate_before_create(env, raw_phone):
    """Check if phone already exists in temer.phone or temer.lead (digit-based, no country_id needed)."""
    if not raw_phone or not str(raw_phone).strip():
        return False
    raw = str(raw_phone).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return False
    e164 = f"+{digits}" if raw.startswith("+") else None
    tail = digits[-10:] if len(digits) >= 10 else (digits[-9:] if len(digits) >= 9 else None)
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
    try:
        if "wing.duplicate.phone.mixin" in env:
            candidate = e164 or raw
            sp, _sup, _msg = env["wing.duplicate.phone.mixin"].sudo()._wing_find_existing_temer_and_old_crm_only(candidate)
            if sp:
                return True
    except Exception:
        pass
    return False


class CrmReception(models.Model):
    _name = "crm.reception"
    _inherit = [
        "crm.reception",
        "wing.duplicate.phone.mixin",
        "wing.sales.team.sms.mixin",
    ]

    def _send_sms(self, mobile_number, message):
        from .wing_sms import send_sms_afromessage
        return send_sms_afromessage(mobile_number, message, env=self.env)

    def _send_sms_for_duplicate(self):
        """Send SMS for duplicate phone numbers automatically using standard Wing logic."""
        self.ensure_one()
        if not self.existing_salesperson_id:
            _logger.info("Wing Reception: skipping SMS for duplicate because no existing_salesperson_id for id=%s.", self.id)
            return

        _logger.info("=== AUTOMATIC SMS FOR DUPLICATE PHONE (RECEPTION) id=%s ===", self.id)
        # Use the unified background sender for existing customers.
        # Always report 'Walk In' in the SMS message (source field is used only for the reception record).
        source_name = "Walk In"
        self.env["wing.existing.customer.sms"].send_for_record_in_background(
            self._name, self.id, source_name
        )

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
        """True if user (or linked partner) has phone/mobile, OR a phone number stored in the email/login field, OR a real email address."""
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
            # Email field may contain a phone number (e.g. '0970414609') or a real email — both count
            if getattr(partner, "email", None) and str(partner.email).strip():
                return True
        # Also check user.login and user.email — in Odoo the "Email Address" on user form = login
        for val in (getattr(user, "email", None), getattr(user, "login", None)):
            if val and str(val).strip():
                return True
        return False

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
        sup_user = None
        if getattr(sup, "_name", None) == "res.users":
            sup_user = sup
        elif getattr(sup, "name", None) and getattr(sup.name, "_name", None) == "res.users":
            sup_user = sup.name
        elif getattr(sup, "user_id", None) and getattr(sup.user_id, "_name", None) == "res.users":
            sup_user = sup.user_id
        if sup_user:
            return self._wing_user_has_phone(sup_user)
        return True

    def _send_sms_to_existing_sales_team(self):
        """Use wing.existing.customer.sms model only (no crm_custom_menu logic). 1 or 2 SMS."""
        wiz = self.env["wing.existing.customer.sms"].create({})
        return wiz.send_for_record(self, "Walk In")

    def action_send_sms_to_existing_customer(self):
        """Same as Website/CallCenter: send 1 or 2 SMS via wing.existing.customer.sms; raise on failure."""
        self.ensure_one()
        if not getattr(self, "phone_number_message", None) or not getattr(self, "existing_salesperson_id", None):
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

    # ------------------------------------------------------------------
    # Override crm_custom_menu automatic lead/SMS so wing handles it.
    # ------------------------------------------------------------------
    def _create_temer_lead_automatically(self):
        """Override base auto lead/SMS: when wing distribution is installed,
        Reception leads are handled by wing logic in _wing_create_lead_and_send_sms,
        so we intentionally skip crm_custom_menu's implementation to avoid
        duplicate SMS or leads."""
        _logger.info(
            "Wing Distribution: skipping crm_custom_menu._create_temer_lead_automatically for reception id(s) %s "
            "(handled by wing _wing_create_lead_and_send_sms).",
            self.ids,
        )
        return

    wing_sms_sent = fields.Boolean(
        string="Wing SMS Sent",
        default=False,
        copy=False,
        help="True when temer.lead and SMS were created/sent by wing distribution",
    )

    def _wing_create_lead_and_send_sms(self, phone_override=None):
        """Create temer.lead and send SMS when wing distribution assigns (new_phone already cleared)."""
        self.ensure_one()
        _logger.info(
            "Wing Distribution: _wing_create_lead_and_send_sms rec=%s wing_sms_sent=%s state_crm=%s nominee=%s full_phone=%s phone_override=%s",
            self.id, self.wing_sms_sent, self.state_crm, self.nominated_salesperson_id.id if self.nominated_salesperson_id else None,
            len(self.full_phone) if self.full_phone else 0, bool(phone_override),
        )
        if self.wing_sms_sent:
            _logger.warning("Wing Distribution: skipping lead/SMS for rec=%s (wing_sms_sent=True)", self.id)
            return
        if self.state_crm != "draft":
            _logger.warning("Wing Distribution: skipping lead/SMS for rec=%s (state_crm=%s != draft)", self.id, self.state_crm)
            return
        if not self.nominated_salesperson_id:
            _logger.warning("Wing Distribution: skipping lead/SMS for rec=%s (no nominated_salesperson_id)", self.id)
            return
        raw_phone = (self.full_phone[0].name if self.full_phone else None) or (str(phone_override) if phone_override else None)
        if not raw_phone:
            _logger.warning("Wing Distribution: skipping lead/SMS for rec=%s (no phone: full_phone=%s phone_override=%s)", self.id, bool(self.full_phone), phone_override)
            return

        def _normalize_phone(p):
            if not p or not str(p).strip():
                return None
            # Standard prefix stripping: +251, 251, 0, spaces
            digits = "".join(ch for ch in str(p) if ch.isdigit())
            if not digits:
                return None
            if digits.startswith("251") and len(digits) > 9:
                digits = digits[3:]
            if digits.startswith("0") and len(digits) > 9:
                digits = digits[1:]
            return digits if len(digits) >= 9 else None

        clean_phone = _normalize_phone(raw_phone)
        if not self.customer_name or not self.customer_name.strip() or not clean_phone:
            _logger.warning("Wing Distribution: skipping lead/SMS for rec=%s (no customer_name or empty clean_phone)", self.id)
            return
        # If we already identified this as an existing customer, trigger SMS and skip lead creation.
        is_duplicate = bool(
            getattr(self, "phone_number_message", None) and (self.phone_number_message or "").strip()
        ) or bool(getattr(self, "existing_salesperson_id", None)) or bool(
            getattr(self, "existing_temer_lead_id", None)
        ) or _is_duplicate_before_create(self.env, raw_phone)
        if is_duplicate:
            _logger.info("Wing Reception: duplicate detected in _wing_create_lead_and_send_sms. Triggering SMS.")
            self._send_sms_for_duplicate()
            return
        # Regardless of what the reception record source is set to, create the lead as Walk In
        # and always label SMS messages as Walk In.
        source = self.env["utm.source"].search([("name", "=", "Walk In")], limit=1)
        source_id = source.id if source else False
        source_name = "Walk In"
        # Always use the nominated salesperson as the lead owner — never the reception/creator user.
        assigned_user = self.nominated_salesperson_id
        lead_values = {
            "name": self.name or f"Lead from {self.customer_name.strip()}",
            "customer_name": self.customer_name.strip(),
            "phone_no": clean_phone,
            "site_ids": [(6, 0, self.site_ids.ids)],
            "country_id": self.country_id.id,
            "source_ids": source_id,
            "user_id": assigned_user.id if assigned_user else False,
            "state": "prospect",
            "from_reception": True,
        }
        lead = False
        supervisor_to_notify = self.nominated_supervisor_id or self._wing_get_supervisor_for_salesperson(
            self.nominated_salesperson_id
        )
        if not supervisor_to_notify:
            raise ValidationError(
                _(
                    "No supervisor found for the nominated salesperson. "
                    "Please assign a supervisor and try again."
                )
            )
        try:
            # Use sudo + explicit user_id so the lead is always owned by the salesperson,
            # regardless of which user (e.g. reception) is performing the create.
            lead = self.env["temer.lead"].sudo().with_context(
                mail_create_nosubscribe=True,
                mail_create_nolog=True,
                tracking_disable=True,
            ).create(lead_values)
            _logger.info("Wing Distribution: creating temer.lead and sending SMS for reception id=%s", self.id)
            self.write({"nominated_supervisor_id": supervisor_to_notify.id})

            sales_ok, err_msg = self._send_sales_team_sms_from_record(
                source=source_name,
                is_existing=False,
                lead=lead,
                customer_phone_override=clean_phone,
            )
            if not sales_ok:
                _logger.warning(
                    "Wing Distribution: SMS reported failure for reception id=%s (%s). Lead kept; not blocking.",
                    self.id,
                    err_msg or "unknown",
                )
                try:
                    self._wing_release_distribution_slot("walk_in")
                except Exception:
                    pass

            # Persist lead; only mark as sent when SMS actually succeeded.
            write_vals = {
                "assigned_salesperson_id": self.nominated_salesperson_id.id,
                "assigned_wing_id": self.nominated_wing_id.id if self.nominated_wing_id else False,
                "assigned_supervisor_id": supervisor_to_notify.id if supervisor_to_notify else False,
            }
            if sales_ok:
                write_vals.update({"wing_sms_sent": True, "state_crm": "sent"})
            self.write(write_vals)
        except Exception as e:
            _logger.error("Wing Distribution: error creating lead/sending SMS: %s", str(e))
            # Best-effort cleanup so no orphan lead or unwanted reception is left.
            try:
                if lead and lead.exists():
                    lead.sudo().unlink()
            except Exception:
                _logger.exception("Wing Distribution: failed to cleanup temer.lead after error.")
            # When called during initial create, also discard the newly created reception record.
            if self.env.context.get("wing_from_create"):
                try:
                    self.unlink()
                except Exception:
                    _logger.exception("Wing Distribution: failed to cleanup crm.reception after error.")
            # Re-raise so that the Reception operation is rolled back in the UI.
            raise

    assigned_salesperson_name = fields.Char(
        string="Assigned Person Name",
        related="assigned_salesperson_id.partner_id.name",
        readonly=True,
    )
    assigned_salesperson_phone = fields.Char(
        string="Assigned Person Phone",
        related="assigned_salesperson_id.partner_id.phone",
        readonly=True,
    )
    assigned_supervisor_name = fields.Char(
        string="Assigned Salesperson Supervisor",
        related="assigned_supervisor_id.name.name",
        readonly=True,
    )
    wing_duplicate_popup_pending = fields.Boolean(
        string="Duplicate Popup Pending",
        default=False,
        copy=False,
        help="Internal flag: show duplicate popup once after detecting existing customer.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("Wing Distribution: reception create called, count=%s.", len(vals_list))
        # Validation: block save when no active wing config (show error, do not use old algo)
        if not self._has_active_walkin_distribution_lines():
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Reception. "
                    "Please add a Walk In / Reception distribution type with active users in Wing Distribution, or activate existing lines. Lead not created."
                )
            )
        allowed_users = self._get_active_walkin_users()
        if not allowed_users:
            raise UserError(
                _(
                    "No active salesperson in Wing Distribution for Reception. "
                    "Please add users to Walk In distribution lines or activate them. Lead not created."
                )
            )
        def _norm_phone(val):
            if not val or not str(val).strip():
                return None
            p = str(val).strip()
            digits = "".join(ch for ch in p if ch.isdigit())
            if not digits:
                return None
            # Standard prefix stripping: 251, 0
            if digits.startswith("251") and len(digits) > 9:
                digits = digits[3:]
            if digits.startswith("0") and len(digits) > 9:
                digits = digits[1:]
            return digits if len(digits) >= 9 else None

        def _has_phone_in_vals(vals):
            if _norm_phone(vals.get("new_phone")) or _norm_phone(vals.get("phone_number")):
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

        # Require phone number before save - block create completely if no phone.
        # Duplicate handling is delegated to base crm_custom_menu logic so that
        # "Duplicate Phone Information" (Existing Salesperson/Supervisor) continues to work.
        for vals in vals_list:
            if not _has_phone_in_vals(vals):
                raise UserError(_("Please insert a phone number."))
        # Reception users are constrained by crm_custom_menu to use source 'Walk In'.
        # Workaround: create the record as Walk In (to satisfy constraints), then sudo-update
        # it to the desired source so the field value (and SMS/lead) reflect the chosen source.
        reception_group = self.env.ref("crm_custom_menu.group_reception", raise_if_not_found=False)
        is_reception_user = bool(reception_group and self.env.user in reception_group.users)
        walk_in_source = None
        if is_reception_user:
            walk_in_source = self.env["utm.source"].search([("name", "=", "Walk In")], limit=1)

        records = self.env["crm.reception"]
        phones_from_vals = {}  # reception_id -> clean phone (fallback when full_phone empty)
        for vals in vals_list:
            _logger.info("Wing Distribution: create vals keys=%s new_phone=%s phone_number=%s", list(vals.keys()), vals.get("new_phone"), vals.get("phone_number"))

            desired_source_id = None
            if (
                is_reception_user
                and walk_in_source
                and vals.get("source_id")
                and vals.get("source_id") != walk_in_source.id
            ):
                desired_source_id = vals.get("source_id")
                vals["source_id"] = walk_in_source.id

            # Robust phone extraction for proactive duplicate check
            phone_raw = vals.get("new_phone") or vals.get("phone_number")
            if not phone_raw and vals.get("full_phone"):
                try:
                    fp = vals.get("full_phone")
                    if fp and isinstance(fp, (list, tuple)):
                        for cmd in fp:
                            # 0 is 'create' command in Many2many
                            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 0 and isinstance(cmd[2], dict):
                                phone_raw = (cmd[2].get("name") or "").strip()
                                if phone_raw:
                                    break
                except Exception:
                    pass

            is_dup_before = False
            if phone_raw:
                try:
                    is_dup_before = self.env["wing.duplicate.phone.mixin"]._wing_find_existing_temer_and_old_crm_only(phone_raw)[2]
                except Exception:
                    pass
            
            ctx = dict(self.env.context)
            if is_dup_before:
                ctx["wing_skip_distribution_for_duplicate"] = True
            
            phone_override = _norm_phone(phone_raw)
            rec = super(CrmReception, self.with_context(ctx)).create(vals)
            if desired_source_id:
                try:
                    super(CrmReception, rec.sudo()).write({"source_id": desired_source_id})
                except Exception:
                    _logger.exception(
                        "Wing Distribution: failed to set desired source for reception id=%s", rec.id
                    )
            if not phone_override and rec.phone_number:
                phone_override = _norm_phone(rec.phone_number)
            if phone_override:
                phones_from_vals[rec.id] = phone_override
            records |= rec
        for rec in records:
            # Sync country on phone records so Customer Phones tab can show Country per row
            if rec.full_phone and rec.country_id:
                for phone in rec.full_phone:
                    if hasattr(phone, "country_id") and not phone.country_id:
                        phone.country_id = rec.country_id.id

            # Ensure we backfill duplicate info from temer.lead/old CRM if possible (like other modules do).
            try:
                raw = ""
                if getattr(rec, "new_phone", None):
                    raw = str(rec.new_phone).strip()
                if not raw and getattr(rec, "full_phone", None) and rec.full_phone:
                    raw = (rec.full_phone[0].name or "").strip()
                if raw and hasattr(rec, "_wing_backfill_duplicate_owner_from_phone"):
                    rec._wing_backfill_duplicate_owner_from_phone(raw)
            except Exception:
                _logger.exception(
                    "Wing Distribution: _wing_backfill_duplicate_owner_from_phone failed for reception id=%s — "
                    "existing_salesperson_id may not be set, duplicate detection incomplete.",
                    rec.id,
                )

            is_duplicate = bool(
                getattr(rec, "phone_number_message", None) and (rec.phone_number_message or "").strip()
            ) or bool(getattr(rec, "existing_salesperson_id", None)) or bool(
                getattr(rec, "existing_temer_lead_id", None)
            )
            if is_duplicate:
                _logger.info(
                    "Wing Distribution: reception id=%s duplicate (existing customer), skipping assignment and lead/SMS.",
                    rec.id,
                )
                # Ensure user sees the duplicate popup (and a clear message if salesperson has no phone)
                try:
                    msg = rec._wing_duplicate_message_for_salesperson(
                        getattr(rec, "existing_salesperson_id", None)
                    )
                except Exception:
                    msg = None

                # Prefer draft state until we know SMS is successfully sent.
                # Schedule SMS sending in the background (same behavior as Website/Call Center).
                try:
                    rec._wing_release_distribution_slot("walk_in")
                except Exception:
                    pass

                existing_salesperson = getattr(rec, "existing_salesperson_id", None)
                has_sp_phone = bool(existing_salesperson and rec._wing_user_has_phone(existing_salesperson))

                try:
                    rec.write(
                        {
                            "wing_duplicate_popup_pending": True,
                            # Clear assignment so duplicates do not reserve a distribution slot.
                            "nominated_salesperson_id": False,
                            "nominated_wing_id": False,
                            "nominated_supervisor_id": False,
                            "assigned_salesperson_id": False,
                            "assigned_wing_id": False,
                            "assigned_supervisor_id": False,
                            # Keep draft until SMS send succeeds (immediately or in background).
                            "state_crm": "draft",
                            "wing_sms_sent": False,
                            **({"phone_number_message": msg} if msg else {}),
                        }
                    )
                except Exception:
                    pass

                model_name, res_id, src = rec._name, rec.id, "Walk In"
                env = rec.env

                if has_sp_phone:
                    try:
                        success, err_msg = env["wing.existing.customer.sms"].create({}).send_for_record(
                            rec, src
                        )
                        if success:
                            rec.write(
                                {
                                    "state_crm": "sent",
                                    "wing_sms_sent": True,
                                }
                            )
                            continue
                        _logger.warning(
                            "Wing Distribution: existing-customer SMS failed for reception id=%s: %s",
                            rec.id,
                            err_msg or "unknown",
                        )
                    except Exception:
                        _logger.exception(
                            "Wing Distribution: error sending existing-customer SMS immediately for reception id=%s.",
                            rec.id,
                        )

                def _schedule_sms():
                    env["wing.existing.customer.sms"].send_for_record_in_background(
                        model_name, res_id, "Walk In"
                    )

                env.cr.postcommit.add(_schedule_sms)
                continue
            if rec._has_active_walkin_distribution_lines():
                _logger.info("Wing Distribution: reception id=%s has active walk-in lines, checking assignment.", rec.id)
                allowed_users = rec._get_active_walkin_users()
                nominee_valid = bool(
                    rec.nominated_salesperson_id
                    and rec.nominated_salesperson_id in allowed_users
                    and rec._wing_user_has_supervisor(rec.nominated_salesperson_id)
                )
                if not nominee_valid:
                    user, config = rec._get_next_user_by_weighted_team("walk_in")
                    if user:
                        rec.write(
                            {
                                "nominated_salesperson_id": user.id,
                                "nominated_wing_id": config.id if config else False,
                                "assigned_via_wing_distribution": True,
                            }
                        )
                        _logger.info(
                            "Wing Distribution: reception id=%s nominated user=%s wing_config=%s.",
                            rec.id,
                            user.name,
                            config.display_name if config else None,
                        )
                    else:
                        raise UserError(
                            _(
                                "No active salesperson with supervisor in Wing Distribution for Reception. "
                                "Please assign supervisors to active users or activate a valid user. Lead not created."
                            )
                        )
                else:
                    _logger.info(
                        "Wing Distribution: reception id=%s nominee already set and in allowed list, no reassignment.",
                        rec.id,
                    )
            if not rec.assigned_salesperson_id and rec.nominated_salesperson_id:
                rec.write(
                    {
                        "assigned_salesperson_id": rec.nominated_salesperson_id.id,
                        "assigned_wing_id": rec.nominated_wing_id.id
                        if rec.nominated_wing_id
                        else False,
                    }
                )
            # Create temer.lead and send SMS (crm_custom_menu skips when new_phone cleared; wing handles it)
            phone_fallback = phones_from_vals.get(rec.id)
            has_phone = bool(rec.full_phone) or bool(phone_fallback)
            will_call = rec.nominated_salesperson_id and has_phone and rec._has_active_walkin_distribution_lines()
            _logger.info(
                "Wing Distribution: rec=%s lead/SMS check: nominee=%s full_phone=%s phone_fallback=%s will_call=%s",
                rec.id, bool(rec.nominated_salesperson_id), bool(rec.full_phone), bool(phone_fallback), will_call,
            )
            if will_call:
                # Mark context so _wing_create_lead_and_send_sms knows this came from initial create;
                # on failure it will best-effort discard both the lead and the newly created reception.
                rec.with_context(wing_from_create=True)._wing_create_lead_and_send_sms(phone_override=phone_fallback)
        return records

    # Keys that cause base write() to re-run assignment and mark "served" - must not reach base on update
    _WRITE_TRIGGER_KEYS = {"customer_name", "site_ids", "new_phone", "full_phone"}

    def write(self, vals):
        # Assignment only on create; on update do not run algorithm and do not set "served"
        if not vals:
            return True

        # Allow Reception users to set a non-Walk In source even if crm_custom_menu enforces Walk In.
        reception_group = self.env.ref("crm_custom_menu.group_reception", raise_if_not_found=False)
        is_reception_user = bool(reception_group and self.env.user in reception_group.users)
        walk_in_source = None
        desired_source_id = None
        if is_reception_user:
            walk_in_source = self.env["utm.source"].search([("name", "=", "Walk In")], limit=1)
            if walk_in_source and "source_id" in vals and vals.get("source_id") and vals.get("source_id") != walk_in_source.id:
                desired_source_id = vals.get("source_id")
                vals["source_id"] = walk_in_source.id

        assignment_keys = {"nominated_salesperson_id", "assigned_salesperson_id"}
        if assignment_keys & set(vals):
            return super().write(vals)
        trigger_in_vals = self._WRITE_TRIGGER_KEYS & set(vals)
        preserve = trigger_in_vals and any(
            rec._has_active_walkin_distribution_lines()
            and (rec.nominated_salesperson_id or rec.assigned_salesperson_id)
            for rec in self
        )
        if preserve:
            # Block save when draft would have no phone after this write
            def _norm_phone(val):
                if not val or not str(val).strip():
                    return None
                p = str(val).strip()
                digits = "".join(ch for ch in p if ch.isdigit())
                if not digits:
                    return None
                # Standard prefix stripping: 251, 0
                if digits.startswith("251") and len(digits) > 9:
                    digits = digits[3:]
                if digits.startswith("0") and len(digits) > 9:
                    digits = digits[1:]
                return digits if len(digits) >= 9 else None
            for rec in self:
                if rec.state_crm != "draft":
                    continue
                will_have_phone = False
                if _norm_phone(vals.get("new_phone")):
                    will_have_phone = True
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
                if not will_have_phone and not rec.full_phone and not _norm_phone(rec.new_phone):
                    raise UserError(_("Please insert a phone number."))
            # Duplicate-phone handling (setting phone_number_message, existing_salesperson_id,
            # existing_supervisor_id, etc.) is handled by the base crm_custom_menu write().
            # Let base process new_phone (add to full_phone and clear field); other trigger keys applied below
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
            
            # Clear new_phone after base write added it to Customer Phones
            if "new_phone" in vals:
                self._write({"new_phone": ""})
            # After base write, sync country on phone records when phone or country changed
            if vals.get("new_phone") or vals.get("country_id"):
                for rec in self:
                    if rec.full_phone and rec.country_id:
                        for phone in rec.full_phone:
                            if hasattr(phone, "country_id") and not phone.country_id:
                                phone.country_id = rec.country_id.id
            # When draft: new_phone or full_phone added → create lead and send SMS (like crm_custom_menu)
            phone_fallback = None
            if "new_phone" in vals and vals.get("new_phone"):
                try:
                    p = str(vals["new_phone"]).strip()
                    digits = "".join(ch for ch in p if ch.isdigit())
                    if digits.startswith("251") and len(digits) > 9:
                        digits = digits[3:]
                    if digits.startswith("0") and len(digits) > 9:
                        digits = digits[1:]
                    phone_fallback = digits if len(digits) >= 9 else None
                except Exception:
                    pass
            phone_added = bool(phone_fallback) or ("full_phone" in vals and vals.get("full_phone"))
            for rec in self:
                if rec.state_crm == "draft" and rec._has_active_walkin_distribution_lines() and not rec.wing_sms_sent:
                    has_phone = bool(rec.full_phone) or bool(phone_fallback)
                    if has_phone and phone_added:
                        # Ensure nominee when added via full_phone (base only assigns on new_phone/customer_name/site_ids)
                        if not rec.nominated_salesperson_id:
                            user, config = rec._get_next_user_by_weighted_team("walk_in")
                            if user:
                                rec.write({
                                    "nominated_salesperson_id": user.id,
                                    "nominated_wing_id": config.id if config else False,
                                    "assigned_via_wing_distribution": True,
                                })
                                sup = rec.env["property.sales.supervisor"].search([("name", "=", user.id)], limit=1)
                                rec.write({"nominated_supervisor_id": sup.id if sup else False})
                                rec.write({"assigned_salesperson_id": user.id, "assigned_wing_id": config.id if config else False, "assigned_supervisor_id": sup.id if sup else False})
                        if rec.nominated_salesperson_id:
                            rec._wing_create_lead_and_send_sms(phone_override=phone_fallback)
            # Apply trigger fields that must not re-run base logic: use same values except new_phone → False (base already cleared it and added to Customer Phones).
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
            if desired_source_id:
                try:
                    super(CrmReception, self.sudo()).write({"source_id": desired_source_id})
                except Exception:
                    _logger.exception(
                        "Wing Distribution: failed to set desired source during write for reception records"
                    )
            return res
        res = super().write(vals)
        # Clear new_phone after normal write (even if new_phone is set to empty string)
        if "new_phone" in vals:
            self._write({"new_phone": ""})
        # Generic sync when not in preserve branch
        if "new_phone" in vals or "country_id" in vals:
            for rec in self:
                if rec.full_phone and rec.country_id:
                    for phone in rec.full_phone:
                        if hasattr(phone, "country_id") and not phone.country_id:
                            phone.country_id = rec.country_id.id
        # Ensure the field is cleared when we already have a phone in Customer Phones
        for rec in self:
            if rec.full_phone and rec.new_phone:
                rec._write({"new_phone": ""})
        if desired_source_id:
            try:
                super(CrmReception, self.sudo()).write({"source_id": desired_source_id})
            except Exception:
                _logger.exception(
                    "Wing Distribution: failed to set desired source during write for reception records"
                )
        return res

    def action_add_phone_and_save(self):
        """Action for the 'Add/Save' button next to the phone field."""
        self.ensure_one()
        # write() already handles formatting, duplicate check, assignment, and clearing new_phone.
        # We just need to trigger it. If new_phone is empty, it acts as a normal save.
        self.write({})
        return True

    def _get_next_available_rr_user_and_config(self):
        """Use wing distribution when walk-in config exists; else do not nominate (no base fallback)."""
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            _logger.info("Wing Distribution (Reception): suppression active (existing customer detected); skipping assignment.")
            return (False, False)
        if self._has_active_walkin_distribution_lines():
            _logger.info("Wing Distribution: using weighted assignment (walk-in active).")
            return self._get_next_user_by_weighted_team("walk_in")
        _logger.info(
            "Wing Distribution (Reception): no wing config or no active users in wing config; not nominating."
        )
        return (False, False)

    # Source name for wing config lookup by distribution type code (walk_in, website, 6033, affiliate)
    _WING_DISTRIBUTION_SOURCE_BY_CODE = {"walk_in": "Walk In", "website": "Website", "6033": "6033", "affiliate": "Referral", "social": "Social Media"}

    def _get_next_user_by_weighted_team(self, type_code="walk_in"):
        """Pick next user by weighted wing. type_code: walk_in, website, 6033, affiliate."""
        # Use sudo so lead save does not require Wing Distribution access (privilege only for menu)
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

        # Get or create current round (status = started). New registrations during round are not included.
        current_round = DistributionRound.search(
            [("distribution_type_id", "=", dist_type.id), ("status", "=", "started")],
            limit=1,
            order="id desc",
        )
        if not current_round:
            # Ensure stale/leftover round assignments are cleared so all active users can join the new round.
            # (Some lines may remain with a round_id or status='served' if a previous round didn't finish cleanly.)
            stale_lines = lines.filtered(lambda l: l.round_id or l.status == "served")
            if stale_lines:
                stale_lines.sudo().write({"round_id": False, "status": False})

            # Lines eligible for next round: new or null status, not already in a round
            lines_to_join = lines.filtered(
                lambda l: l.status in (False, "new") and not l.round_id
            )
            if not lines_to_join:
                _logger.info("Wing Distribution: no eligible lines (new/null) for a new round.")
                return False, False
            # Start a new round and assign eligible lines to this round (snapshot)
            next_num = (
                DistributionRound.search_count(
                    [("distribution_type_id", "=", dist_type.id)]
                )
                + 1
            )
            current_round = DistributionRound.sudo().create(
                {
                    "name": "Round %d" % next_num,
                    "distribution_type_id": dist_type.id,
                    "status": "started",
                    "date_started": fields.Datetime.now(),
                }
            )
            _logger.info(
                "Wing Distribution: round started %s, lines_joined=%s.",
                current_round.name,
                len(lines_to_join),
            )
            lines_to_join.sudo().write({"round_id": current_round.id})
            # Normalize: treat "new" as not-served for this round (we only use round_id to know who is in)
            lines_to_join.sudo().write({"status": False})

        # Remaining = lines in this round not yet served (do not consider lines outside round)
        remaining_lines = lines.filtered(
            lambda l: l.round_id == current_round and not l.status
        )
        _logger.info(
            "Wing Distribution: round=%s remaining_lines=%s.",
            current_round.name,
            len(remaining_lines),
        )
        if not remaining_lines:
            # Round finished: reset all lines in this round, mark round served, next call will start new round
            self._finish_wing_distribution_round(current_round, dist_type, lines)
            _logger.info("Wing Distribution: round %s finished.", current_round.name)
            return self._get_next_user_by_weighted_team(type_code)

        # Skip lines with missing salesperson or missing supervisor (new leads only).
        invalid_lines = self.env["wing.distribution.line"]
        for l in remaining_lines:
            has_sup = self._wing_user_has_supervisor(l.user_id)
            has_phone = self._wing_user_has_phone(l.user_id) if l.user_id else False
            sup = self._wing_get_supervisor_for_salesperson(l.user_id) if l.user_id else False
            sup_user = None
            if sup:
                if getattr(sup, "_name", None) == "res.users":
                    sup_user = sup
                elif getattr(sup, "name", None) and getattr(sup.name, "_name", None) == "res.users":
                    sup_user = sup.name
            sup_phone = self._wing_user_has_phone(sup_user) if sup_user else False
            _logger.info(
                "Wing Distribution eligibility: line=%s user=%s has_phone=%s sup=%s sup_user=%s sup_phone=%s => has_supervisor=%s",
                l.id,
                getattr(l.user_id, "name", None),
                has_phone,
                getattr(sup, "id", None),
                getattr(sup_user, "name", None) if sup_user else None,
                sup_phone,
                has_sup,
            )
            if not has_sup:
                invalid_lines |= l
        if invalid_lines:
            invalid_lines.sudo().write({"status": "served"})
            _logger.warning(
                "Wing Distribution (type=%s): skipped %s line(s) with missing salesperson/supervisor/phone.",
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
                    "Wing Distribution (type=%s): no eligible salespeople with supervisors/phone. Assignment aborted.",
                    type_code,
                )
                return False, False

        # Build wing -> remaining lines (only lines in current round, not served)
        wing_remaining_map = {}
        for line in remaining_lines:
            if not line.wing_id:
                continue
            wing_remaining_map.setdefault(
                line.wing_id, self.env["wing.distribution.line"]
            )
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

        # Weight only at round start: once any line in this round is served, do not recalculate until round finishes.
        round_lines = lines.filtered(lambda l: l.round_id == current_round)
        round_has_served = any(l.status == "served" for l in round_lines)
        if not round_has_served:
            # First assignment in this round: compute weight once and store (used for whole round).
            for wing, wing_lines in wing_remaining_map.items():
                state = state_by_wing.get(wing.id)
                if not state:
                    state = TeamState.sudo().create(
                        {
                            "wing_id": wing.id,
                            "distribution_type_id": dist_type.id,
                        }
                    )
                    state_by_wing[wing.id] = state
                weight = len(wing_lines) / float(total_count)
                state.sudo().write(
                    {
                        "supervisor_count": len(wing_lines),
                        "weight": weight,
                        "active": True,
                    }
                )
                _logger.info(
                    "Wing Distribution: wing=%s count=%s weight=%.4f total=%s (round start, fixed for round).",
                    wing.name,
                    len(wing_lines),
                    weight,
                    total_count,
                )
        else:
            # Same round, reuse existing weight (do not recalculate).
            for wing in wing_remaining_map:
                state = state_by_wing.get(wing.id)
                if not state:
                    state = TeamState.sudo().create(
                        {
                            "wing_id": wing.id,
                            "distribution_type_id": dist_type.id,
                        }
                    )
                    state_by_wing[wing.id] = state
                # If weight is 0 (stale/new state), recalculate so the wing isn't stuck at 0.
                if not state.weight:
                    wing_lines = wing_remaining_map[wing]
                    weight = len(wing_lines) / float(total_count)
                    state.sudo().write({"supervisor_count": len(wing_lines), "weight": weight, "active": True})
                else:
                    state.sudo().write({"active": True})
            _logger.info(
                "Wing Distribution: reusing fixed weights for round %s (no recalculation until round finish).",
                current_round.name,
            )

        active_states = [
            state_by_wing[wing_id] for wing_id in wing_ids if wing_id in state_by_wing
        ]
        candidate_states = [state for state in active_states if not state.status]
        if not candidate_states and active_states:
            TeamState.sudo().browse([state.id for state in active_states]).write(
                {"status": False}
            )
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

        chosen_line = random.choice(available_lines)
        chosen_line.sudo().write({"status": "served"})
        chosen_state.sudo().write({"status": "served"})
        _logger.info(
            "Wing Distribution (type=%s): assigned user=%s wing=%s round=%s.",
            type_code,
            chosen_line.user_id.name,
            chosen_wing.name,
            current_round.name,
        )

        source_name = self._WING_DISTRIBUTION_SOURCE_BY_CODE.get(type_code, "Walk In")
        config = self._get_wing_config_for_source(chosen_wing, source_name)
        # For log: use all lines in round per wing so Served/Total is e.g. 1/4 not 0/3
        round_wing_map = {}
        for line in lines.filtered(lambda l: l.round_id == current_round):
            if line.wing_id:
                round_wing_map.setdefault(
                    line.wing_id, self.env["wing.distribution.line"]
                )
                round_wing_map[line.wing_id] |= line
        self._log_wing_distribution_state(
            dist_type,
            round_wing_map,
            state_by_wing,
            chosen_wing,
            chosen_state,
            chosen_line,
        )

        # If all wings served this round, reset wing statuses only (round finishes when all lines served)
        if active_states and all(state.status == "served" for state in active_states):
            TeamState.sudo().browse([state.id for state in active_states]).write(
                {"status": False}
            )

        # If all lines in this round are now served, finish round (next call will start new round)
        still_remaining = lines.filtered(
            lambda l: l.round_id == current_round and not l.status
        )
        if not still_remaining:
            self._finish_wing_distribution_round(current_round, dist_type, lines)

        return chosen_line.user_id, config

    def _finish_wing_distribution_round(self, round_record, dist_type, all_lines):
        """Mark round as served, clear line statuses and round_id, so next round can start. Uses sudo so reception user needs no round access."""
        lines_in_round = all_lines.filtered(lambda l: l.round_id == round_record)
        if lines_in_round:
            lines_in_round.sudo().write({"status": False, "round_id": False})
            _logger.info(
                "Wing Distribution: round %s finished, %s lines reset (status=False, round_id=False).",
                round_record.name,
                len(lines_in_round),
            )
        round_record.sudo().write(
            {"status": "served", "date_served": fields.Datetime.now()}
        )
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
            for idx, state in enumerate(sorted_states):
                if state.wing_id.id == last_wing_id:
                    next_state = sorted_states[(idx + 1) % len(sorted_states)]
                    Param.set_param(key, str(next_state.wing_id.id))
                    return next_state
            # last_wing_id not in current candidates — pick next by ID, wrap around if needed
            greater = [s for s in sorted_states if s.wing_id.id > last_wing_id]
            next_state = greater[0] if greater else sorted_states[0]
            Param.set_param(key, str(next_state.wing_id.id))
            return next_state
        Param.set_param(key, str(sorted_states[0].wing_id.id))
        return sorted_states[0]

    def _get_active_distribution_users(self, type_code):
        """Return all users in active distribution lines for this type. Uses sudo so lead save does not require Wing Distribution access."""
        DistributionType = self.env["wing.distribution.type"].sudo()
        DistributionLine = self.env["wing.distribution.line"].sudo()
        dist_type = DistributionType.search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = DistributionType.search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            return self.env["res.users"]
        lines = DistributionLine.search(
            [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
        )
        return lines.mapped("user_id")

    def _get_active_walkin_users(self):
        return self._get_active_distribution_users("walk_in")

    def _has_active_distribution_lines(self, type_code):
        """True if there is at least one active distribution line for this type. Uses sudo so lead save does not require Wing Distribution access."""
        DistributionType = self.env["wing.distribution.type"].sudo()
        DistributionLine = self.env["wing.distribution.line"].sudo()
        dist_type = DistributionType.search([("code", "=", type_code)], limit=1)
        if not dist_type:
            dist_type = DistributionType.search([("name", "ilike", type_code)], limit=1)
        if not dist_type:
            return False
        return bool(
            DistributionLine.search_count(
                [("distribution_type_ids", "in", [dist_type.id]), ("active", "=", True)]
            )
        )

    def _has_active_walkin_distribution_lines(self):
        return self._has_active_distribution_lines("walk_in")

    def _log_wing_distribution_state(
        self, dist_type, round_wing_map, state_by_wing, chosen_wing, chosen_state, chosen_line
    ):
        """round_wing_map: wing -> all lines in current round for that wing (so Served/Total is correct)."""
        header = "Wing Distribution state (type=%s)" % (dist_type.name)
        rows = ["Wing | Count | Weight | Wing Status | Lines Served/Total"]
        for wing, wing_lines in round_wing_map.items():
            state = state_by_wing.get(wing.id)
            served_count = len(wing_lines.filtered(lambda l: l.status == "served"))
            total_count = len(wing_lines)
            weight = state.weight if state else 0.0
            wing_status = state.status if state else ""
            rows.append(
                "%s | %s | %.4f | %s | %s/%s"
                % (
                    wing.name or "None",
                    total_count,
                    weight,
                    wing_status or "",
                    served_count,
                    total_count,
                )
            )
        _logger.info("%s\n%s", header, "\n".join(rows))
        chosen_total = len(round_wing_map.get(chosen_wing, self.env["wing.distribution.line"]))
        _logger.info(
            "Wing Distribution assignment: wing=%s weight=%.4f users=%s chosen=%s",
            chosen_wing.name if chosen_wing else "None",
            chosen_state.weight,
            chosen_total,
            chosen_line.user_id.name if chosen_line.user_id else "None",
        )

    def _get_wing_config_for_source(self, wing, source_name):
        """Get property.wing.config for given wing and lead source (e.g. Walk In, Website, 6033)."""
        WingConfig = self.env["property.wing.config"]
        if wing:
            config = WingConfig.search(
                [
                    ("source_id.name", "=", source_name),
                    ("wing_id", "=", wing.id),
                ],
                limit=1,
            )
            if config:
                return config
        return WingConfig.search([("source_id.name", "=", source_name)], limit=1)

    def _get_walkin_config_for_wing(self, wing):
        return self._get_wing_config_for_source(wing, "Walk In")
