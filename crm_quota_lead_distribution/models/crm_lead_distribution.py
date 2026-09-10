# -*- coding: utf-8 -*-
"""
Shared lead distribution logic (same models as lead_distrubtion folder):
  crm.lead.quota, crm.wing.member, crm.team.rotation
"""
import logging
import re
from decimal import ROUND_HALF_UP, Decimal

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from odoo.addons.crm_custom_menu_customer_phone.models import (
    crm_customer_phone_mixin as phone_util,
)


_logger = logging.getLogger(__name__)

TYPE_WALKIN = "walkin"
TYPE_WEBSITE = "website"
TYPE_CALLCENTER = "call_center"

SOURCE_BY_TYPE = {
    TYPE_WALKIN: "Walk In",
    TYPE_WEBSITE: "Website",
    TYPE_CALLCENTER: "6033",
}


class CrmLeadDistribution(models.AbstractModel):
    _name = "crm.lead.distribution"
    _description = "Lead distribution (quota ratio + rotation)"

    nominated_sales_wing_id = fields.Many2one(
        "property.sales.wing",
        string="Nominated Wing",
        readonly=True,
        copy=False,
    )
    assigned_sales_wing_id = fields.Many2one(
        "property.sales.wing",
        string="Assigned Wing",
        readonly=True,
        copy=False,
    )
    status = fields.Char(string="Status", readonly=True, copy=False)
    reassign_lead = fields.Boolean(
        string="Reassign Lead",
        compute="_compute_reassign_lead",
        store=False,
    )
    display_salesperson_id = fields.Many2one(
        "res.users",
        string="Assigned Salesperson",
        compute="_compute_assignment_display",
        store=False,
    )
    display_salesperson_phone = fields.Char(
        string="Salesperson Phone",
        compute="_compute_assignment_display",
        store=False,
    )
    display_supervisor_id = fields.Many2one(
        "property.sales.supervisor",
        string="Supervisor",
        compute="_compute_assignment_display",
        store=False,
    )
    existing_salesperson_phone = fields.Char(
        string="Existing Salesperson Phone",
        compute="_compute_existing_salesperson_phone",
        store=False,
    )
    quota_duplicate_popup_pending = fields.Boolean(
        string="Show Duplicate Wizard",
        default=False,
        copy=False,
    )

    @api.depends("existing_salesperson_id", "existing_salesperson_id.partner_id")
    def _compute_existing_salesperson_phone(self):
        for rec in self:
            rec.existing_salesperson_phone = (
                rec._user_mobile(rec.existing_salesperson_id) or ""
            )

    @api.depends(
        "state_crm",
        "nominated_salesperson_id",
        "assigned_salesperson_id",
        "nominated_supervisor_id",
        "assigned_supervisor_id",
        "phone_number_message",
        "existing_salesperson_id",
    )
    def _compute_assignment_display(self):
        for rec in self:
            rec.display_salesperson_id = False
            rec.display_salesperson_phone = ""
            rec.display_supervisor_id = False
            if rec.phone_number_message and rec.existing_salesperson_id:
                continue
            if rec.state_crm == "sent" and rec.assigned_salesperson_id:
                user = rec.assigned_salesperson_id
                sup = rec.assigned_supervisor_id
            else:
                user = rec.nominated_salesperson_id
                sup = rec.nominated_supervisor_id
            if not sup and user:
                sup = rec.get_supervisor_id(user)
            rec.display_salesperson_id = user
            rec.display_salesperson_phone = rec._user_mobile(user) or ""
            rec.display_supervisor_id = sup

    def _existing_temer_lead_is_lost_or_expired(self):
        self.ensure_one()
        lead = self.existing_temer_lead_id
        return bool(lead and lead.state in ("lost", "expired"))

    @api.model
    def _duplicate_inactive_status_message(self, salesperson):
        if salesperson and not salesperson.active:
            return _(
                "The existing salesperson account is inactive. "
                "Please reassign the lead."
            )
        return False

    @api.model
    def _duplicate_lost_expired_status_message(self, temer_lead):
        if temer_lead and temer_lead.state in ("lost", "expired"):
            return _("The lead is in Lost/Expired state. Please reassign.")
        return False

    @api.model
    def _duplicate_inactive_write_vals(self, status_message, temer_lead=None):
        """Doc CASE 1.C — clear existing salesperson display."""
        vals = {
            "phone_number_message": False,
            "existing_salesperson_id": False,
            "existing_supervisor_id": False,
            "status": status_message,
            "state_crm": "draft",
        }
        if temer_lead and "existing_temer_lead_id" in self._fields:
            vals["existing_temer_lead_id"] = temer_lead.id
        return vals

    @api.model
    def _duplicate_active_owner_write_vals(self, vals_or_phone, esp, esup, etl, status=False):
        """Doc CASE 1.A — keep existing salesperson name/phone on the form."""
        msg = self._get_duplicate_phone_message(self._phone_from_vals(vals_or_phone))
        write_vals = {
            "phone_number_message": msg or _("Existing customer."),
            "existing_salesperson_id": esp.id,
            "existing_supervisor_id": esup.id if esup else False,
            "status": status or False,
            "state_crm": "draft",
        }
        if etl and "existing_temer_lead_id" in self._fields:
            write_vals["existing_temer_lead_id"] = etl.id
        return write_vals

    @api.depends("status")
    def _compute_reassign_lead(self):
        for rec in self:
            rec.reassign_lead = bool((rec.status or "").strip())

    # -------------------------------------------------------------------------
    # Quota algorithm (lead_distrubtion/crm_lead.py)
    # -------------------------------------------------------------------------

    def _distribution_type(self):
        return {
            "crm.reception": TYPE_WALKIN,
            "crm.website": TYPE_WEBSITE,
            "crm.callcenter": TYPE_CALLCENTER,
        }.get(self._name, TYPE_WALKIN)

    def _channel_label(self, stype):
        labels = dict(
            self.env["crm.lead.quota"]._fields["type"].selection
        )
        return labels.get(stype, stype)

    def _distribution_member_domain(self, stype, wing=None):
        """Domain for crm.wing.member rows eligible for assignment (extensible)."""
        domain = [("type", "=", stype), ("active", "=", True)]
        if wing:
            domain.append(("team_id", "=", wing.id))
        return domain

    def _active_distribution_users(self, stype, wing=None):
        """
        Eligible assignees = rows in Distribution Configuration only.

        A user is included only when BOTH are true:
        - crm.wing.member.active (member row checked in Distribution Configuration)
        - res.users.active (Odoo user account not archived)

        All other res.users are ignored (not in rotation).
        """
        Member = self.env["crm.wing.member"].sudo()
        members = Member.search(
            self._distribution_member_domain(stype, wing), order="sequence asc"
        )
        return members.mapped("user_id").filtered(lambda u: u and u.active)

    def _teams_with_active_members(self, teams, stype):
        """Team quota rows whose wing has at least one active distribution member."""
        eligible = self.env["crm.lead.quota"]
        for team in teams:
            wing = team.team_id
            if wing and self._active_distribution_users(stype, wing):
                eligible |= team
        return eligible

    def _validation_error_no_active_users(self, stype):
        channel = self._channel_label(stype)
        Quota = self.env["crm.lead.quota"].sudo()
        Member = self.env["crm.wing.member"].sudo()
        quota_n = Quota.search_count([("type", "=", stype), ("active", "=", True)])
        members_n = Member.search_count(
            [("type", "=", stype), ("active", "=", True)]
        )
        with_team_n = Member.search_count(
            [
                ("type", "=", stype),
                ("active", "=", True),
                ("team_id", "!=", False),
            ]
        )
        missing_team = members_n - with_team_n
        detail = []
        if not quota_n:
            detail.append(
                _("- Lead_Qouta: no active row for type “%(type)s”.") % {"type": stype}
            )
        if not members_n:
            detail.append(
                _(
                    "- Distribution Configuration: no active member for “%(type)s”."
                )
                % {"type": stype}
            )
        elif missing_team:
            detail.append(
                _(
                    "- Distribution Configuration: %(n)s member(s) have no Team "
                    "(Team column empty). Fix Property salesperson mapping and "
                    "re-save each member row."
                )
                % {"n": missing_team}
            )
        elif quota_n and with_team_n:
            detail.append(
                _(
                    "- Quota rows exist but no wing matches a member on the same Team."
                )
            )
        raise ValidationError(
            _(
                "No active user available for %(channel)s lead distribution.\n\n"
                "%(details)s\n\n"
                "Also check: Property → Configuration → Lead_Qouta (active, quota > 0) "
                "and members must not be only the logged-in user."
            )
            % {
                "channel": channel,
                "details": "\n".join(detail)
                if detail
                else _(
                    "Add active Lead_Qouta rows and Distribution Members "
                    "(salesperson active, Team filled)."
                ),
            }
        )

    def _get_ratio(self, quota_rec):
        if not quota_rec.quota:
            return Decimal("0.0000")
        remaining = (quota_rec.quota or 0) - (quota_rec.assigned_count or 0)
        return (Decimal(remaining) / Decimal(quota_rec.quota)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    def _log_quota_ratio_audit(self, stype, teams, candidates, quota_reset):
        """Log each wing's ratio inputs for Odoo server log (grep: Lead distribution [quota])."""
        _logger.info(
            "Lead distribution [quota] channel=%s model=%s active_wings=%s "
            "eligible_wings=%s quota_reset=%s",
            stype,
            self._name,
            len(teams),
            len(candidates),
            quota_reset,
        )
        for quota_rec in teams:
            remaining = (quota_rec.quota or 0) - (quota_rec.assigned_count or 0)
            ratio = self._get_ratio(quota_rec)
            wing_name = quota_rec.team_id.name if quota_rec.team_id else "?"
            eligible = quota_rec in candidates
            _logger.info(
                "Lead distribution [quota] wing=%s quota_id=%s quota=%s "
                "assigned_count=%s remaining=%s ratio=%s eligible=%s",
                wing_name,
                quota_rec.id,
                quota_rec.quota,
                quota_rec.assigned_count,
                remaining,
                ratio,
                eligible,
            )

    def _log_rotation_audit(self, stype, wing, members, users, rotation, last_user, next_user):
        """Log member order and rotation pick (grep: Lead distribution [rotation])."""
        member_lines = ", ".join(
            "%s(seq=%s,id=%s)" % (m.user_id.name, m.sequence, m.user_id.id)
            for m in members
        )
        _logger.info(
            "Lead distribution [rotation] channel=%s wing=%s wing_id=%s "
            "rotation_id=%s members=[%s] active_users=%s",
            stype,
            wing.name,
            wing.id,
            rotation.id,
            member_lines or "(none)",
            len(users),
        )
        _logger.info(
            "Lead distribution [rotation] last_user=%s (id=%s) -> next_user=%s (id=%s)",
            last_user.name if last_user else "(none)",
            last_user.id if last_user else None,
            next_user.name,
            next_user.id,
        )

    def auto_assign_lead(self, source_type=None):
        """Pick wing by highest remaining/quota, then one user from crm.wing.member."""
        stype = source_type or self._distribution_type()
        Quota = self.env["crm.lead.quota"].sudo()
        Rotation = self.env["crm.team.rotation"].sudo()

        teams = Quota.search([("type", "=", stype), ("active", "=", True)])
        active_users = self._active_distribution_users(stype)
        if not teams or not active_users:
            _logger.warning(
                "Lead distribution [quota] channel=%s — no active quota or users "
                "(teams=%s active_users=%s)",
                stype,
                len(teams),
                len(active_users),
            )
            self._validation_error_no_active_users(stype)

        candidates = self._teams_with_active_members(
            teams.filtered(lambda t: t.assigned_count < t.quota),
            stype,
        )
        quota_reset = False
        if not candidates:
            quota_reset = True
            teams.write({"assigned_count": 0})
            candidates = self._teams_with_active_members(teams, stype)

        if not candidates:
            _logger.warning(
                "Lead distribution [quota] channel=%s — no wing with active members",
                stype,
            )
            self._validation_error_no_active_users(stype)

        self._log_quota_ratio_audit(stype, teams, candidates, quota_reset)

        highest_ratio = max(self._get_ratio(t) for t in candidates)
        top_teams = candidates.filtered(lambda t: self._get_ratio(t) == highest_ratio)
        selected = sorted(top_teams, key=lambda t: (t.assigned_count, t.id))[0]
        wing = selected.team_id

        if len(top_teams) > 1:
            tied = ", ".join(
                "%s(assigned=%s,id=%s)"
                % (t.team_id.name, t.assigned_count, t.id)
                for t in top_teams
            )
            _logger.info(
                "Lead distribution [quota] tie ratio=%s — picked wing=%s "
                "(lowest assigned_count, then id); tied: %s",
                highest_ratio,
                wing.name,
                tied,
            )
        else:
            _logger.info(
                "Lead distribution [quota] selected wing=%s quota_id=%s ratio=%s "
                "assigned_count=%s -> %s",
                wing.name,
                selected.id,
                highest_ratio,
                selected.assigned_count,
                (selected.assigned_count or 0) + 1,
            )

        members = self.env["crm.wing.member"].sudo().search(
            self._distribution_member_domain(stype, wing),
            order="sequence asc",
        )
        users = members.mapped("user_id").filtered(
            lambda u: u and u.active and u != self.env.user
        )
        if not users:
            self._validation_error_no_active_users(stype)

        rotation = Rotation.search(
            [("team_id", "=", wing.id), ("type", "=", stype)],
            limit=1,
        )
        if not rotation:
            rotation = Rotation.create({"team_id": wing.id, "type": stype})

        last_user = rotation.last_user_id
        if last_user and last_user not in users:
            _logger.info(
                "Lead distribution [rotation] skip last_user=%s (archived or removed)",
                last_user.name,
            )
            last_user = False
        if not last_user:
            next_user = users[0]
            rotation_reason = "first active user in wing rotation"
        else:
            idx = users.ids.index(last_user.id)
            next_user = users[(idx + 1) % len(users)]
            rotation_reason = "next active user after %s" % last_user.name

        self._log_rotation_audit(stype, wing, members, users, rotation, last_user, next_user)
        _logger.info(
            "Lead distribution [rotation] pick reason: %s",
            rotation_reason,
        )

        # ORM write (not raw SQL) so stored remaining/ratio recompute in Team Quota UI.
        selected.sudo().write(
            {"assigned_count": (selected.assigned_count or 0) + 1}
        )
        rotation.write(
            {
                "last_user_id": next_user.id,
                "last_assigned_at": fields.Datetime.now(),
            }
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "crm_lead_distribution.last_wing_%s" % stype, str(wing.id)
        )
        _logger.info(
            "Lead distribution [result] channel=%s wing=%s user=%s quota_id=%s "
            "assigned_count now=%s",
            stype,
            wing.name,
            next_user.name,
            selected.id,
            (selected.assigned_count or 0) + 1,
        )
        return next_user, wing

    def get_supervisor_id(self, user):
        if not user:
            return False
        Supervisor = self.env["property.sales.supervisor"].sudo()
        Mapping = self.env["property.salesperson.mapping"].sudo()
        sup = Supervisor.search([("name", "=", user.id)], limit=1)
        if sup:
            return sup
        mapping = Mapping.search([("user_id", "=", user.id)], limit=1)
        return mapping.supervisor_id if mapping else False

    def _user_mobile(self, user):
        """
        SMS number for a user.

        Priority (Temer often stores the number in the email/login field):
        1. partner.email, user.email, user.login — if value has no '@', treat as phone
        2. partner/user mobile and phone fields
        """
        if not user:
            return None
        partner = user.partner_id

        for val in (
            getattr(partner, "email", None) if partner else None,
            getattr(user, "email", None),
            getattr(user, "login", None),
        ):
            if not val:
                continue
            s = str(val).strip()
            if s and "@" not in s:
                return s

        for val in (
            getattr(partner, "mobile", None) if partner else None,
            getattr(partner, "phone", None) if partner else None,
            getattr(user, "mobile", None),
            getattr(user, "phone", None),
        ):
            if not val:
                continue
            s = str(val).strip()
            if s and "@" not in s:
                return s
        return None

    def _source_label(self):
        return SOURCE_BY_TYPE.get(self._distribution_type(), "Walk In")

    # -------------------------------------------------------------------------
    # CRM hooks (crm_custom_menu)
    # -------------------------------------------------------------------------

    @api.model
    def _norm_phone_val(self, value):
        return (value or "").strip()

    @api.model
    def _has_phone_in_vals(self, vals):
        """True when vals include a phone (same rules as wing_distribution_configuration)."""
        if self._norm_phone_val(vals.get("new_phone")) or self._norm_phone_val(
            vals.get("phone_no")
        ):
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
                        if self._norm_phone_val(cmd[2].get("name")):
                            return True
        return False

    @api.model
    def _require_phone_in_vals_list(self, vals_list):
        for vals in vals_list:
            if not self._has_phone_in_vals(vals):
                raise UserError(_("Please insert a phone number."))

    @api.model
    def _phone_from_vals(self, vals):
        return phone_util.normalize_phone_from_vals(self, vals)

    def _phone_national_digits(self, raw_phone, country=None):
        """Local digits without country prefix (for temer.lead phone_no)."""
        if not raw_phone:
            return ""
        rec = self[:1]
        if country and rec:
            rec = rec.with_context(default_country_id=country.id)
        return phone_util.national_digits_from_raw(rec or self, raw_phone)

    def _fix_full_phone_after_save(self):
        """Drop mistaken +251 row; keep one country-correct Customer Phones line."""
        for rec in self:
            if not getattr(rec, "new_phone", None):
                continue
            vals = {
                "new_phone": rec.new_phone,
                "country_id": rec.country_id.id if getattr(rec, "country_id", None) else False,
            }
            entry = phone_util.get_new_phone_entry(rec, vals)
            if entry:
                phone_util.apply_correct_customer_phone(rec, entry)
        phone_util.sync_phone_lines_country(self)

    def _channel_assigned_salesperson(self, record):
        """Assigned salesperson on an old CRM row — never the receptionist (sales_person)."""
        user = record.nominated_salesperson_id or record.assigned_salesperson_id
        return user if user and not self._is_login_user(user) else False

    def _is_login_user(self, user):
        return bool(user and user == self.env.user)

    def _assignment_clear_vals(self):
        clear = {
            "nominated_salesperson_id": False,
            "nominated_supervisor_id": False,
            "nominated_wing_id": False,
            "nominated_sales_wing_id": False,
            "assigned_salesperson_id": False,
            "assigned_supervisor_id": False,
            "assigned_wing_id": False,
            "assigned_sales_wing_id": False,
        }
        if "wing_sms_sent" in self._fields:
            clear["wing_sms_sent"] = True
        return clear

    @api.model
    def _phone_lookup_variants(self, vals_or_phone):
        return phone_util.phone_lookup_variants(self, vals_or_phone)

    def _find_channel_record_by_phone(self, variants, exclude_ids=None):
        """Most recent Reception/Website/Call Center row with this phone."""
        exclude_ids = list(exclude_ids or [])
        if not variants:
            return self.env["crm.reception"]
        phone_models = {
            "crm.reception": "crm.reception.phone",
            "crm.website": "crm.website.phone",
            "crm.callcenter": "crm.callcenter.phone",
        }
        best = None
        best_date = None
        for model_name in ("crm.reception", "crm.website", "crm.callcenter"):
            if model_name not in self.env:
                continue
            Model = self.env[model_name].sudo()
            dom = [("full_phone.name", "in", variants)]
            if exclude_ids:
                dom.append(("id", "not in", exclude_ids))
            rec = Model.search(dom, order="create_date desc", limit=1)
            if not rec:
                phone_model = phone_models.get(model_name)
                if phone_model and phone_model in self.env:
                    lines = self.env[phone_model].sudo().search(
                        [("name", "in", variants)]
                    )
                    if lines:
                        dom2 = [("full_phone", "in", lines.ids)]
                        if exclude_ids:
                            dom2.append(("id", "not in", exclude_ids))
                        rec = Model.search(dom2, order="create_date desc", limit=1)
            if rec and (best_date is None or rec.create_date > best_date):
                best = rec
                best_date = rec.create_date
        return best or self.env["crm.reception"]

    def _lookup_existing_owner(self, vals_or_phone, exclude_ids=None):
        """
        Return (salesperson, supervisor, temer_lead) for duplicate phone.
        CRM channel assignee wins over temer.lead (avoids receptionist as owner).
        """
        exclude_ids = list(exclude_ids or []) + list(self.ids)
        variants = self._phone_lookup_variants(vals_or_phone)

        channel_rec = self._find_channel_record_by_phone(variants, exclude_ids=exclude_ids)

        if channel_rec:
            salesperson = self._channel_assigned_salesperson(channel_rec)
            if salesperson and not self._is_login_user(salesperson):
                supervisor = self._get_supervisor_for_salesperson(salesperson)
                return salesperson, supervisor, False

        TemerLead = self.env["temer.lead"].sudo()
        temer_lead = TemerLead.search(
            [
                ("phone_ids.phone", "in", variants),
                ("state", "not in", ["lost", "expired"]),
            ],
            order="create_date desc",
            limit=1,
        )
        if not temer_lead and variants:
            tail = "".join(ch for ch in variants[0] if ch.isdigit())[-9:]
            if tail:
                temer_lead = TemerLead.search(
                    [
                        ("phone_ids.phone", "ilike", tail),
                        ("state", "not in", ["lost", "expired"]),
                    ],
                    order="create_date desc",
                    limit=1,
                )
        if temer_lead and temer_lead.user_id and not self._is_login_user(temer_lead.user_id):
            salesperson = temer_lead.user_id
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor, temer_lead

        closed_lead = TemerLead.search(
            [
                ("phone_ids.phone", "in", variants),
                ("state", "in", ["lost", "expired"]),
            ],
            order="create_date desc",
            limit=1,
        )
        if not closed_lead and variants:
            tail = "".join(ch for ch in variants[0] if ch.isdigit())[-9:]
            if tail:
                closed_lead = TemerLead.search(
                    [
                        ("phone_ids.phone", "ilike", tail),
                        ("state", "in", ["lost", "expired"]),
                    ],
                    order="create_date desc",
                    limit=1,
                )
        if closed_lead and closed_lead.user_id and not self._is_login_user(
            closed_lead.user_id
        ):
            salesperson = closed_lead.user_id
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor, closed_lead

        return None, None, False

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        exclude_ids = list(exclude_ids or []) + list(self.ids)
        if self.env.context.get("quota_treat_as_new"):
            return False
        variants = self._phone_lookup_variants(full_phone_number)
        if not variants:
            return False
        parts = []
        channel_rec = self._find_channel_record_by_phone(variants, exclude_ids=exclude_ids)
        if channel_rec:
            sp = self._channel_assigned_salesperson(channel_rec)
            label = {
                "crm.reception": _("Reception CRM"),
                "crm.website": _("Website CRM"),
                "crm.callcenter": _("Call Center CRM"),
            }.get(channel_rec._name, channel_rec._name)
            if sp:
                parts.append(
                    _("In %(source)s registered by: %(name)s.")
                    % {"source": label, "name": sp.name}
                )
        TemerLead = self.env["temer.lead"].sudo()
        tl = TemerLead.search(
            [
                ("phone_ids.phone", "in", variants),
                ("state", "not in", ["lost", "expired"]),
            ],
            order="create_date desc",
            limit=1,
        )
        if tl and tl.user_id and not self._is_login_user(tl.user_id):
            temer_line = _("In Temer Leads registered by: %(name)s.") % {
                "name": tl.user_id.name
            }
            if not any(temer_line in p for p in parts):
                parts.append(temer_line)
        return self._normalize_duplicate_message(
            "\n".join(parts) if parts else False
        )

    @staticmethod
    def _normalize_duplicate_message(msg):
        """One line per registration source (readable in popup)."""
        if not msg:
            return ""
        text = (msg or "").replace("\r", "").strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) > 1:
            return "\n".join(lines)
        parts = re.split(r"(?<=\.)\s+", text)
        parts = [p.strip() for p in parts if p.strip()]
        return "\n".join(parts) if parts else text

    def _get_existing_salesperson_info(self, full_phone_number):
        if self.env.context.get("quota_treat_as_new"):
            return None, None, False
        return self._lookup_existing_owner(full_phone_number)

    @api.model
    def _is_duplicate_vals(self, vals):
        if self.env.context.get("quota_treat_as_new"):
            return False
        variants = self._phone_lookup_variants(vals)
        if not variants:
            return False
        if self._find_channel_record_by_phone(variants):
            return True
        if self._get_duplicate_phone_message(variants[0]):
            return True
        if "temer.phone" in self.env:
            tail = "".join(ch for ch in variants[0] if ch.isdigit())[-9:]
            if tail and self.env["temer.phone"].sudo().search_count(
                ["|", ("phone", "in", variants), ("phone", "ilike", tail)]
            ):
                return True
        return False

    @api.model
    def _check_duplicate_owner_or_error(self, vals):
        """Block save when duplicate exists but owner is missing or the login user."""
        esp, _, _ = self._lookup_existing_owner(vals)
        if not esp:
            raise UserError(
                _(
                    "This phone number is already registered.\n"
                    "No assigned salesperson was found for this phone."
                )
            )
        if self._is_login_user(esp):
            raise UserError(
                _(
                    "This phone number is already registered.\n"
                    "No valid assigned salesperson was found "
                    "(the logged-in user cannot be used).\n"
                    "No lead was assigned and no message was sent."
                )
            )
        return esp

    @api.model
    def _enrich_full_phone_create_vals(self, vals):
        """Country-aware full_phone (not hardcoded +251)."""
        vals = dict(vals)
        entry = phone_util.get_new_phone_entry(self, vals)
        if entry:
            vals["full_phone"] = [(4, entry.id)]
        return vals

    @api.model
    def _prepare_duplicate_vals(self, vals):
        """Mark duplicate; never pre-assign the logged-in user."""
        vals = dict(vals)
        if not self._is_duplicate_vals(vals):
            return vals, False
        self._check_duplicate_owner_or_error(vals)
        esp, esup, etl = self._lookup_existing_owner(vals)
        vals.update(self._assignment_clear_vals())
        vals = self._enrich_full_phone_create_vals(vals)
        inactive_msg = self._duplicate_inactive_status_message(esp)
        if inactive_msg:
            vals.update(self._duplicate_inactive_write_vals(inactive_msg, etl))
        elif self._duplicate_lost_expired_status_message(etl):
            vals.update(
                self._duplicate_active_owner_write_vals(
                    vals,
                    esp,
                    esup,
                    etl,
                    status=self._duplicate_lost_expired_status_message(etl),
                )
            )
        else:
            vals.update(self._duplicate_active_owner_write_vals(vals, esp, esup, etl))
        return vals, True

    def _quota_apply_duplicate(self):
        """Existing customer per spec: display, status/reassign, in-app notify (no SMS)."""
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
            write_vals = self._duplicate_inactive_write_vals(inactive_msg, etl)
            self.with_context(**skip).write(write_vals)
            self._quota_suppress_wing_duplicate_effects()
            self._mark_duplicate_popup_pending()
            return

        lost_msg = self._duplicate_lost_expired_status_message(etl)
        if lost_msg:
            write_vals = self._duplicate_active_owner_write_vals(
                lookup, esp, esup, etl, status=lost_msg
            )
            self.with_context(**skip).write(write_vals)
            self._quota_suppress_wing_duplicate_effects()
            self._mark_duplicate_popup_pending()
            return

        write_vals = self._duplicate_active_owner_write_vals(lookup, esp, esup, etl)
        self.with_context(**skip).write(write_vals)
        self._quota_suppress_wing_duplicate_effects()

        sales_ok, err_msg = self._send_sales_team_sms_via_wing(
            source=self._source_label(),
            is_existing=True,
            salesperson_override=esp,
            supervisor_override=esup,
            lead=self,
        )
        if not sales_ok:
            raise UserError(
                err_msg
                or _(
                    "Could not send SMS to the assigned sales team about this "
                    "duplicate contact. The record remains in Draft."
                )
            )
        self.with_context(**skip).write({"state_crm": "sent"})
        self._mark_duplicate_popup_pending()
        _logger.info(
            "Lead distribution [duplicate] existing=%s — SMS sent",
            esp.name,
        )

    def _mark_duplicate_popup_pending(self):
        """Open duplicate wizard via JS after save (no yellow banner on form)."""
        if self.env.context.get("quota_skip_mark_pending"):
            return
        to_flag = self.filtered(
            lambda r: (
                (
                    (r.phone_number_message or "").strip()
                    or r.existing_salesperson_id
                    or (r.status or "").strip()
                )
                and not r.quota_duplicate_popup_pending
            )
        )
        if not to_flag:
            return
        wing_off = {}
        if "wing_duplicate_popup_pending" in to_flag._fields:
            wing_off["wing_duplicate_popup_pending"] = False
        to_flag.with_context(
            quota_skip_mark_pending=True,
            quota_skip_phone_notify=True,
        ).write({"quota_duplicate_popup_pending": True, **wing_off})

    def _supervisor_user_from_record(self, supervisor_rec):
        """property.sales.supervisor → res.users."""
        if not supervisor_rec:
            return self.env["res.users"]
        if supervisor_rec._name == "property.sales.supervisor":
            return supervisor_rec.name
        if supervisor_rec._name == "res.users":
            return supervisor_rec
        return self.env["res.users"]

    def _customer_phone_display(self):
        """Phone string for notification text (international when possible)."""
        self.ensure_one()
        if self.full_phone:
            name = (self.full_phone[0].name or "").strip()
            if name:
                return name
        national = self._phone_national_digits(
            self.new_phone or getattr(self, "phone_no", "") or "",
            self.country_id if getattr(self, "country_id", None) else None,
        )
        if national and getattr(self, "country_id", None) and self.country_id.phone_code:
            return "+%s%s" % (self.country_id.phone_code, national)
        return national or (self.new_phone or "")

    def _send_realtime_notify(self, users, subject, body):
        """Toast popup for online users (Discuss inbox is separate from form chatter)."""
        bus = self.env["bus.bus"].sudo()
        payload = {
            "title": subject,
            "message": body,
            "sticky": False,
            "type": "info",
        }
        for user in users:
            if user.partner_id:
                bus._sendone(user.partner_id, "simple_notification", payload)

    def _post_notify_chatter_summary(self, users, subject, body):
        """Log on the CRM record so operators see confirmation in chatter."""
        if not self or not hasattr(self, "message_post"):
            return
        names = ", ".join(users.mapped("name")) or _("recipients")
        summary = _(
            "Assignment notification sent to %(names)s.<br/>"
            "<b>%(subject)s</b><br/>%(body)s"
        ) % {"names": names, "subject": subject, "body": body}
        try:
            self.sudo().message_post(
                body=Markup(summary),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
        except Exception as exc:
            _logger.warning(
                "Lead distribution [notify] chatter log failed: %s", exc
            )

    def _notify_users_inbox(self, users, subject, body):
        """In-app notify; never includes the logged-in user."""
        users = users.sudo().filtered(
            lambda u: u and u.active and u.partner_id and not self._is_login_user(u)
        )
        if not users:
            return False
        html_body = Markup("<p>%s</p>") % body
        try:
            messages = self.sudo().message_notify(
                partner_ids=users.mapped("partner_id").ids,
                subject=subject,
                body=html_body,
                subtype_xmlid="mail.mt_note",
            )
            if not messages:
                _logger.warning(
                    "Lead distribution [notify] message_notify returned no message "
                    "(recipients=%s)",
                    ", ".join(users.mapped("login")),
                )
                return False
            self._send_realtime_notify(users, subject, body)
            self._post_notify_chatter_summary(users, subject, body)
            return True
        except Exception as exc:
            _logger.warning(
                "Lead distribution [notify] message_notify failed: %s", exc
            )
            return False

    def _notify_user_inbox(self, user, subject, body):
        if user and not self._is_login_user(user):
            return self._notify_users_inbox(user, subject, body)
        return False

    def _user_is_wing_or_team_manager(self, user):
        """True if user is wing manager or sales team manager (treated like supervisor)."""
        if not user:
            return False
        Wing = self.env["property.sales.wing"].sudo()
        if Wing.search_count([("manager_id", "=", user.id)]):
            return True
        Team = self.env["property.sales.team"].sudo()
        if Team.search_count([("manager_id", "=", user.id)]):
            return True
        if self.env["property.sales.supervisor"].sudo().search_count(
            [("name", "=", user.id)]
        ):
            return True
        return False

    def _duplicate_notify_single_message_only(self, salesperson, supervisor_user):
        """
        One inbox message when the existing owner is effectively top of chain:
        - wing / team manager
        - same person as mapped supervisor
        - no separate supervisor on file
        """
        if not salesperson:
            return True
        if self._user_is_wing_or_team_manager(salesperson):
            return True
        if not supervisor_user:
            return True
        return supervisor_user.id == salesperson.id

    def _doc_notify_duplicate_active_lead(self, salesperson, supervisor_rec):
        """
        Doc CASE 1.B — same rules as wing SMS (inbox only, no SMS / no API key):
        - Regular salesperson + separate supervisor → 2 inbox messages
        - Salesperson is supervisor or wing/team manager → 1 message only
        Never notify the logged-in user.
        """
        self.ensure_one()
        if not salesperson or self._is_login_user(salesperson):
            return False

        sup_user = self._supervisor_user_from_record(supervisor_rec)
        if not sup_user:
            sup_rec = self._get_supervisor_for_salesperson(salesperson)
            sup_user = self._supervisor_user_from_record(sup_rec)

        single_message = self._duplicate_notify_single_message_only(
            salesperson, sup_user
        )
        src = self._source_label()
        cust = (self.customer_name or "").strip() or _("Customer")
        phone = self._customer_phone_display()
        sales_name = salesperson.name or _("Salesperson")
        subject = _("Existing customer contact")

        sales_body = _(
            "Hi %(sales)s, Customer: %(cust)s (%(phone)s) came via %(source)s. "
            "Please follow up."
        ) % {
            "sales": sales_name,
            "cust": cust,
            "phone": phone,
            "source": src,
        }
        sales_ok = self._notify_user_inbox(salesperson, subject, sales_body)
        sup_ok = True
        if not single_message and sup_user:
            sup_body = _(
                "Hi %(super)s, salesperson under your supervision %(sales)s's "
                "customer contacted us via %(source)s. Please follow up."
            ) % {
                "super": sup_user.name or _("Supervisor"),
                "sales": sales_name,
                "source": src,
            }
            sup_ok = self._notify_user_inbox(sup_user, subject, sup_body)

        ok = sales_ok and sup_ok
        if ok:
            recipients = [salesperson.login]
            if not single_message and sup_user:
                recipients.append(sup_user.login)
            _logger.info(
                "Lead distribution [duplicate] notified (%s message(s)): %s",
                len(recipients),
                ", ".join(recipients),
            )
        else:
            _logger.warning(
                "Lead distribution [duplicate] notify failed (channel=%s, "
                "salesperson_ok=%s, supervisor_ok=%s)",
                self._distribution_type(),
                sales_ok,
                sup_ok,
            )
        return ok

    def _notify_new_lead_assigned(self):
        """New assignment: one inbox message to assigned salesperson only (not supervisor)."""
        self.ensure_one()
        salesperson = self.nominated_salesperson_id
        if not salesperson or self._is_login_user(salesperson):
            return False
        src = self._source_label()
        cust = (self.customer_name or "").strip() or _("Customer")
        phone = self._customer_phone_display()
        body = _(
            "Hi %(sales)s, New lead from %(source)s: Customer %(cust)s (%(phone)s). "
            "Please follow up."
        ) % {
            "sales": salesperson.name or _("Salesperson"),
            "source": src,
            "cust": cust,
            "phone": phone,
        }
        if self._notify_user_inbox(salesperson, _("New lead assigned"), body):
            _logger.info(
                "Lead distribution [assign] notified salesperson=%s",
                salesperson.login,
            )
            return True
        _logger.warning(
            "Lead distribution [assign] notify failed for salesperson=%s",
            salesperson.login,
        )
        return False

    def _send_sales_team_sms_via_wing(
        self,
        source=None,
        is_existing=False,
        lead=None,
        customer_phone_override=None,
        salesperson_override=None,
        supervisor_override=None,
    ):
        """AfroMessage SMS via Login (crm.channel.notify.mixin on channel records)."""
        self.ensure_one()
        if hasattr(self, "_send_sales_team_sms_from_record"):
            return self._send_sales_team_sms_from_record(
                source=source or self._source_label(),
                is_existing=is_existing,
                lead=lead or self,
                customer_phone_override=customer_phone_override,
                salesperson_override=salesperson_override,
                supervisor_override=supervisor_override,
            )
        return False, _("SMS not available on this record.")

    def _send_sms(self, mobile_number, message):
        from .lead_afromessage_sms import send_sms_afromessage
        return send_sms_afromessage(mobile_number, message, env=self.env)

    def _send_sms_to_existing_sales_team(self):
        """Wing hook — send AfroMessage SMS to existing owner + supervisor."""
        self.ensure_one()
        return self._send_sales_team_sms_via_wing(
            is_existing=True,
            lead=self,
        )

    def _quota_send_team_notifications_from_record(
        self,
        source=None,
        is_existing=False,
        lead=None,
        customer_phone_override=None,
        salesperson_override=None,
        supervisor_override=None,
    ):
        """Send AfroMessage SMS (same as wing distribution)."""
        return self._send_sales_team_sms_via_wing(
            source=source,
            is_existing=is_existing,
            lead=lead,
            customer_phone_override=customer_phone_override,
            salesperson_override=salesperson_override,
            supervisor_override=supervisor_override,
        )

    def _quota_suppress_wing_duplicate_effects(self):
        """Stop wing module second popup/SMS when quota handles duplicates."""
        vals = {}
        if "wing_duplicate_popup_pending" in self._fields:
            vals["wing_duplicate_popup_pending"] = False
        if "wing_sms_sent" in self._fields:
            vals["wing_sms_sent"] = True
        if vals:
            self.with_context(
                quota_skip_phone_notify=True, quota_skip_apply_wing=True
            ).write(vals)

    def _quota_assign_next_user(self):
        """
        Quota + rotation assignment (replaces crm_custom_menu property.wing.config RR).
        Returns (res.users, False) — second value is legacy wing.config slot, unused.
        """
        if self.env.context.get("lead_distribution_skip_assign"):
            _logger.info(
                "Lead distribution [assign] skipped (duplicate phone) model=%s",
                self._name,
            )
            return False, False
        stype = self._distribution_type()
        _logger.info(
            "Lead distribution [assign] start model=%s channel=%s (quota module)",
            self._name,
            stype,
        )
        try:
            user, wing = self.auto_assign_lead(stype)
        except ValidationError as e:
            raise UserError(str(e)) from e
        if not user:
            self._validation_error_no_active_users(stype)
        if self._is_login_user(user):
            raise UserError(
                _(
                    "Lead distribution cannot assign the lead to you (logged-in user).\n"
                    "Add other active salespeople under Distribution Members for this channel."
                )
            )
        if wing:
            self.env["ir.config_parameter"].sudo().set_param(
                "crm_lead_distribution.last_wing_%s" % stype, str(wing.id)
            )
        return user, False

    def _get_next_available_rr_user_and_config(self):
        """Override crm_custom_menu round-robin (property.wing.config)."""
        return self._quota_assign_next_user()

    def _wing_config_for_sales_wing(self, wing):
        """
        Map property.sales.wing → property.wing.config for this channel.

        Lead Distribution report reads assigned_wing_id (wing config), not sales wing.
        """
        WingConfig = self.env["property.wing.config"].sudo()
        if not wing:
            return WingConfig.browse()
        source_name = self._source_label()
        if hasattr(self, "_get_wing_config_for_source"):
            return self._get_wing_config_for_source(wing, source_name)
        config = WingConfig.search(
            [("source_id.name", "=", source_name), ("wing_id", "=", wing.id)],
            limit=1,
        )
        if config:
            return config
        return WingConfig.browse()

    def _supervisor_for_assigned_wing(self, user, wing):
        """Supervisor only when their team belongs to the quota-assigned sales wing."""
        sup = self.get_supervisor_id(user)
        if not sup or not wing:
            return sup
        team = sup.sales_team_id
        if team and team.wing_id == wing:
            return sup
        _logger.info(
            "Lead distribution: skip nominated supervisor %s (team wing %s != assigned %s)",
            sup.name,
            team.wing_id.name if team and team.wing_id else None,
            wing.name,
        )
        return False

    @api.constrains(
        "nominated_supervisor_id",
        "nominated_wing_id",
        "nominated_sales_wing_id",
    )
    def _check_supervisor_in_wing(self):
        """
        Quota assigns property.sales.wing (nominated_sales_wing_id).
        Legacy crm_custom_menu compared wing.config vs supervisor team — mismatch
        when wing.config row is missing or points at another wing.
        """
        channel_models = ("crm.reception", "crm.website", "crm.callcenter")
        for rec in self:
            if rec._name not in channel_models:
                continue
            sup = rec.nominated_supervisor_id
            if not sup:
                continue
            wing = rec.nominated_sales_wing_id
            if not wing and rec.nominated_wing_id:
                wing = rec.nominated_wing_id.wing_id
            if not wing:
                continue
            team = sup.sales_team_id
            if not team:
                raise ValidationError(
                    _("Selected supervisor is not linked to any sales team!")
                )
            if team.wing_id != wing:
                raise ValidationError(
                    _(
                        "Selected supervisor is not assigned to any team "
                        "under the selected wing!"
                    )
                )

    def _write_nominated_wing_fields(self, user, wing):
        """Set salesperson + wing fields; skip write() wing hook (avoids recursion)."""
        if self._is_login_user(user):
            raise UserError(
                _(
                    "Cannot assign this lead to the logged-in user.\n"
                    "Check Team Quota and Distribution Members."
                )
            )
        wing_id = wing.id if wing else False
        wing_config = self._wing_config_for_sales_wing(wing)
        wing_config_id = wing_config.id if wing_config else False
        sup = self._supervisor_for_assigned_wing(user, wing)
        self.with_context(quota_skip_apply_wing=True).write(
            {
                "nominated_salesperson_id": user.id if user else False,
                "nominated_sales_wing_id": wing_id,
                "assigned_sales_wing_id": wing_id,
                "nominated_wing_id": wing_config_id,
                "assigned_wing_id": False,
                "nominated_supervisor_id": sup.id if sup else False,
            }
        )

    def _apply_wing_after_assign(self, records):
        """Sync wing from last quota rotation (config param) after assign."""
        Wing = self.env["property.sales.wing"].sudo()
        for rec in records:
            if not rec.nominated_salesperson_id:
                continue
            stype = rec._distribution_type()
            wing_id = int(
                rec.env["ir.config_parameter"]
                .sudo()
                .get_param("crm_lead_distribution.last_wing_%s" % stype, "0")
                or 0
            )
            if not wing_id:
                continue
            wing = Wing.browse(wing_id).exists()
            if wing:
                rec._write_nominated_wing_fields(rec.nominated_salesperson_id, wing)

    def _collect_phone_values(self):
        self.ensure_one()
        phones = []
        for fp in self.full_phone:
            if fp.name and fp.name.strip():
                phones.append(fp.name.strip())
        normalized = self._phone_from_vals(
            {"new_phone": self.new_phone or getattr(self, "phone_no", "") or ""}
        )
        if normalized and normalized not in phones:
            phones.append(normalized)
        return phones

    def _delete_temer_phones(self):
        """Remove phone rows from temer.lead so reassign is treated as a new customer."""
        self.ensure_one()
        if "temer.phone" not in self.env:
            return
        Phone = self.env["temer.phone"].sudo()
        for phone_val in self._collect_phone_values():
            phones = Phone.search(
                ["|", ("phone", "=", phone_val), ("phone", "ilike", phone_val[-9:])]
            )
            if phones:
                phones.unlink()
                _logger.info(
                    "Lead distribution [reassign] removed temer.phone for %s",
                    phone_val,
                )

    def _phone_local_digits(self):
        self.ensure_one()
        if self.full_phone:
            return self._phone_national_digits(
                self.full_phone[0].name, self.country_id
            )
        return self._phone_national_digits(
            self.new_phone or getattr(self, "phone_no", "") or "",
            self.country_id,
        )

    def _inactive_duplicate_message(self):
        sp = self.existing_salesperson_id
        name = sp.name if sp else _("Unknown")
        return _(
            "Existing salesperson %(name)s is archived/inactive. "
            "Click Reassign to treat this customer as a new lead."
        ) % {"name": name}

    def _create_temer_lead_automatically(self):
        """Create temer.lead after AfroMessage SMS succeeds."""
        return self._create_temer_lead_after_sms()

    def _create_temer_lead_after_sms(self):
        """Create temer.lead only after SMS to the assigned salesperson succeeds."""
        self.ensure_one()
        if self.env.context.get("lead_distribution_skip_assign"):
            return
        if self.state_crm != "draft" or not getattr(self, "new_phone", None):
            return
        if (self.status or "").strip() or self.existing_salesperson_id:
            return
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
            "site_ids": [(6, 0, self.site_ids.ids)] if hasattr(self, "site_ids") else [],
            "country_id": self.country_id.id if hasattr(self, "country_id") else False,
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
            raise UserError(
                err_msg
                or _(
                    "Could not send SMS to the assigned salesperson. "
                    "The lead was not created and the record remains in Draft."
                )
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
        wing_id = getattr(self, "nominated_wing_id", False) and self.nominated_wing_id.id
        sales_wing_id = (
            getattr(self, "nominated_sales_wing_id", False)
            and self.nominated_sales_wing_id.id
        )
        sent_vals = {
            "assigned_salesperson_id": self.nominated_salesperson_id.id,
            "assigned_wing_id": wing_id,
            "assigned_sales_wing_id": sales_wing_id,
            "assigned_supervisor_id": (
                supervisor_to_notify.id if supervisor_to_notify else False
            ),
            "state_crm": "sent",
        }
        if self.env.context.get("quota_treat_as_new"):
            self._write_skip_crm_custom_menu(sent_vals)
        else:
            self.with_context(quota_skip_apply_wing=True).write(sent_vals)

    def _send_sms_for_duplicate(self):
        return self._quota_apply_duplicate()

    def action_send_sms_to_existing_customer(self):
        self.ensure_one()
        if self.existing_salesperson_id and not self.existing_salesperson_id.active:
            raise UserError(
                _("Cannot send SMS: existing salesperson is archived. Use Reassign.")
            )
        sales_ok, err_msg = self._send_sms_to_existing_sales_team()
        if not sales_ok:
            raise UserError(err_msg or _("Failed to send SMS."))
        return True

    def action_reassign_lead(self):
        """Delete temer.phone rows, quota-assign once, create new temer.lead."""
        self.ensure_one()
        if not self.reassign_lead:
            raise UserError(
                _(
                    "Re Assign is only available when the lead is lost/expired, "
                    "or the existing salesperson is inactive."
                )
            )
        if not self.customer_name or not self.customer_name.strip():
            raise UserError(_("Customer name is required before reassign."))

        phone_local = self._phone_local_digits()
        if not phone_local:
            raise UserError(_("No phone number on this record to reassign."))

        self._delete_temer_phones()

        treat_ctx = dict(
            quota_skip_apply_wing=True,
            quota_treat_as_new=True,
            quota_skip_phone_notify=True,
        )
        rec = self.with_context(**treat_ctx)

        try:
            user, wing = rec.auto_assign_lead(rec._distribution_type())
        except ValidationError as e:
            raise UserError(str(e)) from e
        if not user:
            rec._validation_error_no_active_users(rec._distribution_type())
        if rec._is_login_user(user):
            raise UserError(
                _(
                    "Cannot assign this lead to the logged-in user.\n"
                    "Check Team Quota and Distribution Members."
                )
            )

        wing_id = wing.id if wing else False
        supervisor = rec.get_supervisor_id(user)
        rec._write_skip_crm_custom_menu(
            {
                "phone_number_message": False,
                "status": False,
                "existing_salesperson_id": False,
                "existing_supervisor_id": False,
                "existing_temer_lead_id": False,
                "state_crm": "draft",
                "quota_duplicate_popup_pending": False,
                "nominated_salesperson_id": user.id,
                "nominated_supervisor_id": supervisor.id if supervisor else False,
                "nominated_wing_id": False,
                "nominated_sales_wing_id": wing_id,
                "assigned_salesperson_id": False,
                "assigned_supervisor_id": False,
                "assigned_wing_id": False,
                "assigned_sales_wing_id": False,
                "new_phone": phone_local,
            }
        )
        rec._fix_full_phone_after_save()
        rec._create_temer_lead_automatically()

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _create_bypass_wing(self, vals, extra_ctx=None):
        """
        Create CRM record without wing hooks.
        Duplicate phones skip crm_custom_menu (avoids temer.lead unique error).
        """
        ctx = dict(
            self.env.context,
            quota_skip_wing_duplicate_backfill=True,
        )
        if extra_ctx:
            ctx.update(extra_ctx)
        env = self.with_context(**ctx)
        if extra_ctx and extra_ctx.get("lead_distribution_skip_assign"):
            _logger.info(
                "Lead distribution [create] model=%s duplicate — skip temer.lead create",
                self._name,
            )
            return super(CrmLeadDistribution, env).create(vals)
        for parent in type(self).mro():
            mod = getattr(parent, "__module__", "") or ""
            if "wing_distribution" in mod:
                continue
            if "crm_quota_lead_distribution" in mod:
                continue
            if "crm_custom_menu" in mod:
                _logger.info(
                    "Lead distribution [create] model=%s via crm_custom_menu (wing skipped)",
                    self._name,
                )
                return parent.create(env, vals)
        raise UserError(
            _("Could not create %(model)s — crm_custom_menu not found in inheritance.")
            % {"model": self._name}
        )

    @api.model_create_multi
    def _quota_create_records(self, vals_list):
        self._require_phone_in_vals_list(vals_list)
        records = self.env[self._name]
        for vals in vals_list:
            vals, is_dup = self._prepare_duplicate_vals(dict(vals))
            ctx = {"lead_distribution_skip_assign": True} if is_dup else {}
            rec = self._create_bypass_wing(vals, ctx)
            if is_dup:
                rec._quota_apply_duplicate()
            else:
                if rec.nominated_salesperson_id and self._is_login_user(
                    rec.nominated_salesperson_id
                ):
                    rec.with_context(quota_skip_apply_wing=True).write(
                        self._assignment_clear_vals()
                    )
                    raise UserError(
                        _(
                            "This lead could not be assigned to the logged-in user.\n"
                            "Add active Distribution Members for this channel."
                        )
                    )
                self._apply_wing_after_assign(rec)
                if rec.state_crm == "draft" and rec.nominated_salesperson_id:
                    rec._create_temer_lead_after_sms()
            records |= rec
        records._fix_full_phone_after_save()
        return records

    def _enrich_full_phone_vals(self, vals):
        """Link full_phone M2M when bypassing crm_custom_menu write on new_phone."""
        vals = dict(vals)
        if not vals.get("new_phone"):
            return vals
        entry = phone_util.get_new_phone_entry(self, vals)
        if entry:
            vals["full_phone"] = [(4, entry.id)]
        return vals

    def _write_skip_crm_custom_menu(self, vals):
        """Reassign: bypass crm_custom_menu RR/duplicate and wing write hooks."""
        vals = self._enrich_full_phone_vals(dict(vals))
        ctx = dict(
            self.env.context,
            quota_treat_as_new=False,
            quota_skip_apply_wing=True,
            quota_skip_phone_notify=self.env.context.get(
                "quota_skip_phone_notify", True
            ),
            lead_distribution_skip_assign=True,
        )
        return models.Model.write(self.with_context(**ctx), vals)

    def write(self, vals):
        if self.env.context.get("quota_treat_as_new"):
            return self._write_skip_crm_custom_menu(vals)
        ctx = {}
        if vals.get("new_phone") or vals.get("phone_no"):
            for rec in self:
                check = {
                    "new_phone": vals.get("new_phone") or rec.new_phone,
                    "country_id": vals.get("country_id")
                    or (rec.country_id.id if rec.country_id else False),
                }
                if not check.get("new_phone"):
                    check["phone_no"] = vals.get("phone_no") or getattr(
                        rec, "phone_no", ""
                    )
                if rec._is_duplicate_vals(check):
                    rec._check_duplicate_owner_or_error(check)
                    ctx["lead_distribution_skip_assign"] = True
                    vals.update(rec._assignment_clear_vals())
                    break
        res = super(CrmLeadDistribution, self.with_context(**ctx)).write(vals)
        if vals.get("new_phone") or vals.get("country_id"):
            self._fix_full_phone_after_save()
        if (
            not ctx.get("lead_distribution_skip_assign")
            and not self.env.context.get("quota_skip_apply_wing")
        ):
            for rec in self:
                if rec.state_crm == "draft" and rec.nominated_salesperson_id:
                    rec._apply_wing_after_assign(rec)
        if ctx.get("lead_distribution_skip_assign"):
            for rec in self:
                rec._quota_apply_duplicate()
        elif (
            not self.env.context.get("quota_skip_phone_notify")
            and (
                vals.get("new_phone")
                or vals.get("phone_no")
                or vals.get("phone_number_message")
            )
        ):
            dup_recs = self.filtered(
                lambda r: (
                    (r.phone_number_message or "").strip()
                    or r.status
                    or r.existing_salesperson_id
                )
            )
            if dup_recs:
                dup_recs._quota_suppress_wing_duplicate_effects()
                dup_recs._mark_duplicate_popup_pending()
        return res
