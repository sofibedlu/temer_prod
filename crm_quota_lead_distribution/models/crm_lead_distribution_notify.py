# -*- coding: utf-8 -*-
import logging
import re

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

_CHANNEL_MODELS = ("crm.reception", "crm.website", "crm.callcenter")
_WING_TYPE_BY_MODEL = {
    "crm.reception": "walk_in",
    "crm.website": "website",
    "crm.callcenter": "6033",
}


class CrmLeadDistributionNotify(models.AbstractModel):
    _inherit = "crm.lead.distribution"

    @api.model
    def _is_plausible_sms_number(self, raw):
        if not raw:
            return False
        s = str(raw).strip()
        if not s or "@" in s:
            return False
        if s.isalpha() and len(s) <= 3:
            return False
        digits = re.sub(r"\D", "", s)
        return len(digits) >= 9

    @api.model
    def _normalize_sms_number(self, raw):
        if not self._is_plausible_sms_number(raw):
            return None
        digits = re.sub(r"\D", "", str(raw).strip())
        if digits.startswith("251") and len(digits) > 9:
            digits = digits[3:]
        if digits.startswith("0") and len(digits) > 9:
            digits = digits[1:]
        return digits if len(digits) >= 9 else None

    @api.model
    def _contact_from_login_only(self, user):
        if not user:
            return None, None
        val = getattr(user, "login", None)
        if not val:
            return None, None
        s = str(val).strip()
        if not s or "@" in s:
            return None, None
        normalized = self._normalize_sms_number(s)
        return (normalized, None) if normalized else (None, None)

    def _user_mobile(self, user):
        return self._contact_from_login_only(user)[0]

    def _has_valid_login_phone(self, user=None):
        user = user or self.nominated_salesperson_id
        return self._is_eligible_assignee(user)

    @api.model
    def _has_active_wing_member(self, user, stype=None):
        """True if user has an active Distribution Configuration row for this channel."""
        if not user:
            return False
        if self._name not in _CHANNEL_MODELS:
            return True
        stype = stype or {
            "crm.reception": "walkin",
            "crm.website": "website",
            "crm.callcenter": "call_center",
        }.get(self._name, "walkin")
        domain = list(self._distribution_member_domain(stype))
        domain.append(("user_id", "=", user.id))
        return bool(self.env["crm.wing.member"].sudo().search_count(domain))

    @api.model
    def _is_eligible_for_sms(self, user):
        """True when Login holds a valid SMS number (salesperson or supervisor)."""
        return bool(self._contact_from_login_only(user)[0])

    @api.model
    def _is_eligible_assignee(self, user, stype=None):
        """
        New-lead SMS retry pool: active wing member with valid Login.
        Does not filter quota/rotation assignment (original algorithm unchanged).
        """
        if not user or not user.active:
            return False
        if self._name in _CHANNEL_MODELS and not self._has_active_wing_member(
            user, stype=stype
        ):
            return False
        return self._is_eligible_for_sms(user)

    def _users_with_valid_login(self, users):
        eligible = users.filtered(lambda u: u and self._is_eligible_for_sms(u))
        for user in users.filtered(lambda u: u):
            if user in eligible:
                continue
            _logger.info(
                "Lead distribution: skip SMS for %s (no valid Login phone)",
                user.name,
            )
        return eligible

    def _member_users_for_assignment(self, members):
        return members.mapped("user_id").filtered(
            lambda u: u and u.active and u != self.env.user
        )

    def _revert_team_rotation_after_failed_sms(self, stype, wing, failed_user):
        """Failed SMS must not consume this user's turn on the next new lead."""
        if not wing or not failed_user:
            return
        members = self.env["crm.wing.member"].sudo().search(
            self._distribution_member_domain(stype, wing), order="sequence asc"
        )
        member_users = self._member_users_for_assignment(members)
        if failed_user not in member_users:
            return
        idx = member_users.ids.index(failed_user.id)
        prev_user = member_users[(idx - 1) % len(member_users)]
        rotation = self.env["crm.team.rotation"].sudo().search(
            [("team_id", "=", wing.id), ("type", "=", stype)], limit=1
        )
        if rotation:
            rotation.write({"last_user_id": prev_user.id})
            _logger.info(
                "Lead distribution: rotation reverted to %s (SMS failed for %s)",
                prev_user.name,
                failed_user.name,
            )

    def _commit_team_rotation_after_success(self, stype, wing, user):
        """After SMS succeeds, last served in wing = user who actually got the lead."""
        if not wing or not user:
            return
        members = self.env["crm.wing.member"].sudo().search(
            self._distribution_member_domain(stype, wing), order="sequence asc"
        )
        member_users = self._member_users_for_assignment(members)
        if user not in member_users:
            return
        rotation = self.env["crm.team.rotation"].sudo().search(
            [("team_id", "=", wing.id), ("type", "=", stype)], limit=1
        )
        if rotation:
            rotation.write(
                {
                    "last_user_id": user.id,
                    "last_assigned_at": fields.Datetime.now(),
                }
            )
            _logger.info(
                "Lead distribution: rotation committed to %s (wing=%s)",
                user.name,
                wing.name,
            )

    def _next_user_with_login_for_sms_retry(self, stype, wing, after_user):
        """Next member with valid Login for this lead only; rotation unchanged."""
        if not wing or not after_user:
            return False, wing
        members = self.env["crm.wing.member"].sudo().search(
            self._distribution_member_domain(stype, wing), order="sequence asc"
        )
        member_users = self._member_users_for_assignment(members)
        if not member_users:
            return False, wing
        start = 0
        if after_user in member_users:
            start = member_users.ids.index(after_user.id) + 1
        for i in range(len(member_users)):
            candidate = member_users[(start + i) % len(member_users)]
            if candidate == after_user:
                continue
            if not self._is_eligible_for_sms(candidate):
                continue
            _logger.info(
                "Lead distribution: SMS retry wing %s -> %s",
                wing.name,
                candidate.name,
            )
            return candidate, wing
        return False, wing

    def _uses_wing_weighted_assignment(self):
        """Quota/location module owns assignment — never wing.distribution.line rotation."""
        return False

    def _mark_wing_line_served(self, user, type_code):
        return

    def _advance_to_next_salesperson(self):
        self.ensure_one()
        if self._name == "crm.reception" and (
            self.existing_salesperson_id or (getattr(self, "status", None) or "").strip()
        ):
            return False
        current = self.nominated_salesperson_id
        type_code = _WING_TYPE_BY_MODEL.get(self._name)
        if type_code and current and hasattr(self, "_wing_release_distribution_slot"):
            try:
                self._wing_release_distribution_slot(type_code)
            except Exception:
                pass
        if self._uses_wing_weighted_assignment():
            for _ in range(50):
                user, config = self._get_next_user_by_weighted_team(type_code)
                if not user:
                    break
                if user == current:
                    continue
                if not self._is_eligible_assignee(user):
                    continue
                if hasattr(self, "_wing_user_has_supervisor") and not self._wing_user_has_supervisor(user):
                    continue
                sup = False
                if hasattr(self, "_wing_get_supervisor_for_salesperson"):
                    sup = self._wing_get_supervisor_for_salesperson(user)
                vals = {
                    "nominated_salesperson_id": user.id,
                    "nominated_wing_id": config.id if config else False,
                    "assigned_via_wing_distribution": True,
                }
                if sup and "nominated_supervisor_id" in self._fields:
                    vals["nominated_supervisor_id"] = sup.id
                self.with_context(quota_skip_apply_wing=True).write(vals)
                if "assigned_salesperson_id" in self._fields:
                    self.with_context(quota_skip_apply_wing=True).write(
                        {
                            "assigned_salesperson_id": user.id,
                            "assigned_wing_id": config.id if config else False,
                        }
                    )
                _logger.info(
                    "Lead distribution: skipped %s, nominated %s",
                    current.name if current else "(none)",
                    user.name,
                )
                return True
            return False
        stype = self._distribution_type()
        wing = getattr(self, "nominated_sales_wing_id", False)
        if not wing or not current:
            return False
        self._revert_team_rotation_after_failed_sms(stype, wing, current)
        user, wing = self._next_user_with_login_for_sms_retry(
            stype, wing, current
        )
        if not user or user == current:
            return False
        self._write_nominated_wing_fields(user, wing)
        _logger.info(
            "Lead distribution: skipped %s, nominated %s",
            current.name if current else "(none)",
            user.name,
        )
        return True

    def _create_temer_lead_after_sms(self):
        if self._name not in _CHANNEL_MODELS:
            return super()._create_temer_lead_after_sms()
        self.ensure_one()
        if self.env.context.get("lead_distribution_skip_assign"):
            return
        for _ in range(50):
            if self.state_crm != "draft" or not getattr(self, "new_phone", None):
                return
            if (self.status or "").strip() or self.existing_salesperson_id:
                return
            if not self.nominated_salesperson_id:
                return
            if not self._is_eligible_assignee(self.nominated_salesperson_id):
                _logger.warning(
                    "Lead distribution: no valid Login for %s on %s, trying next user",
                    self.nominated_salesperson_id.name,
                    self._name,
                )
                if not self._advance_to_next_salesperson():
                    return
                continue
            clean_phone = self._phone_national_digits(self.new_phone, self.country_id)
            if not (self.customer_name or "").strip() or not clean_phone:
                return
            source_id = False
            if hasattr(self, "source_id") and self.source_id:
                source_id = self.source_id.id
            if not source_id:
                label = self._source_label()
                source_id = (
                    self.env["utm.source"].search([("name", "=", label)], limit=1).id
                )
            lead_values = {
                "name": getattr(self, "name", None)
                or "Lead from %s" % self.customer_name.strip(),
                "customer_name": self.customer_name.strip(),
                "phone_no": clean_phone,
                "site_ids": [(6, 0, self.site_ids.ids)]
                if hasattr(self, "site_ids")
                else [],
                "country_id": self.country_id.id
                if hasattr(self, "country_id")
                else False,
                "source_ids": source_id,
                "user_id": self.nominated_salesperson_id.id,
                "state": "prospect",
            }
            if self._name == "crm.reception":
                lead_values["from_reception"] = True
            elif self._name == "crm.website":
                lead_values["from_website"] = True
            elif self._name == "crm.callcenter":
                lead_values["from_callcenter"] = True
            sales_ok, err_msg = self._send_sales_team_sms_via_wing(
                source=self._source_label(),
                is_existing=False,
                customer_phone_override=clean_phone,
                lead=self,
            )
            if not sales_ok:
                _logger.warning(
                    "Lead distribution: SMS failed for %s on %s (%s), trying next user",
                    self.nominated_salesperson_id.name,
                    self._name,
                    err_msg or "unknown",
                )
                if not self._advance_to_next_salesperson():
                    return
                continue
            if getattr(self, "nominated_sales_wing_id", False):
                self._commit_team_rotation_after_success(
                    self._distribution_type(),
                    self.nominated_sales_wing_id,
                    self.nominated_salesperson_id,
                )
            _logger.info(
                "Lead distribution [sms] sent — creating temer.lead for %s (%s)",
                self.nominated_salesperson_id.name,
                clean_phone,
            )
            self.env["temer.lead"].with_user(self.nominated_salesperson_id).with_context(
                mail_create_nosubscribe=True,
                mail_create_nolog=True,
                tracking_disable=True,
            ).create(lead_values)
            supervisor_to_notify = getattr(self, "nominated_supervisor_id", False)
            if not supervisor_to_notify and self.nominated_salesperson_id:
                supervisor_to_notify = self._get_supervisor_for_salesperson(
                    self.nominated_salesperson_id
                )
            sales_wing = getattr(self, "nominated_sales_wing_id", False)
            wing_config = getattr(self, "nominated_wing_id", False)
            if not wing_config and sales_wing:
                wing_config = self._wing_config_for_sales_wing(sales_wing)
            sent_vals = {
                "assigned_salesperson_id": self.nominated_salesperson_id.id,
                "assigned_wing_id": wing_config.id if wing_config else False,
                "assigned_sales_wing_id": sales_wing.id if sales_wing else False,
                "assigned_supervisor_id": (
                    supervisor_to_notify.id if supervisor_to_notify else False
                ),
                "state_crm": "sent",
            }
            if self.env.context.get("quota_treat_as_new"):
                self._write_skip_crm_custom_menu(sent_vals)
            else:
                self.with_context(quota_skip_apply_wing=True).write(sent_vals)
            return
        return

    def _quota_apply_duplicate(self):
        if self._name not in _CHANNEL_MODELS:
            return super()._quota_apply_duplicate()
        self.ensure_one()
        skip = dict(quota_skip_phone_notify=True, quota_skip_apply_wing=True)
        self.with_context(**skip).write(self._assignment_clear_vals())
        lookup = {
            "new_phone": self.new_phone or "",
            "country_id": self.country_id.id if self.country_id else False,
        }
        if not lookup["new_phone"] and self.full_phone:
            lookup["new_phone"] = self.full_phone[0].name
        esp, esup, etl = self._lookup_existing_owner(lookup)
        if not esp:
            return
        inactive_msg = self._duplicate_inactive_status_message(esp)
        if inactive_msg:
            self.with_context(**skip).write(
                self._duplicate_inactive_write_vals(inactive_msg, etl)
            )
            self._quota_suppress_wing_duplicate_effects()
            self._mark_duplicate_popup_pending()
            return
        lost_msg = self._duplicate_lost_expired_status_message(etl)
        if lost_msg:
            self.with_context(**skip).write(
                self._duplicate_active_owner_write_vals(
                    lookup, esp, esup, etl, status=lost_msg
                )
            )
            self._quota_suppress_wing_duplicate_effects()
            self._mark_duplicate_popup_pending()
            return
        self.with_context(**skip).write(
            self._duplicate_active_owner_write_vals(lookup, esp, esup, etl)
        )
        self._quota_suppress_wing_duplicate_effects()
        if not self._is_eligible_for_sms(esp):
            _logger.info(
                "Lead distribution: duplicate owner %s has no valid Login phone, skip SMS",
                esp.name,
            )
            self._mark_duplicate_popup_pending()
            return
        sales_ok, _err = self._send_sales_team_sms_via_wing(
            source=self._source_label(),
            is_existing=True,
            salesperson_override=esp,
            supervisor_override=esup,
            lead=self,
        )
        if sales_ok:
            self.with_context(**skip).write({"state_crm": "sent"})
        self._mark_duplicate_popup_pending()

    def _send_sales_team_sms_via_wing(
        self,
        source=None,
        is_existing=False,
        lead=None,
        customer_phone_override=None,
        salesperson_override=None,
        supervisor_override=None,
    ):
        self.ensure_one()
        return self._send_sales_team_sms_from_record(
            source=source or self._source_label(),
            is_existing=is_existing,
            lead=lead or self,
            customer_phone_override=customer_phone_override,
            salesperson_override=salesperson_override,
            supervisor_override=supervisor_override,
        )
