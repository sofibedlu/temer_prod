# -*- coding: utf-8 -*-
import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TYPE_WALKIN = "walkin"


class CrmLeadDistributionLocation(models.AbstractModel):
    _inherit = "crm.lead.distribution"

    def _reception_existing_visit_location(self, vals_or_phone):
        """Location from the existing reception row for this phone (existing customer)."""
        variants = self._phone_lookup_variants(vals_or_phone)
        if not variants:
            return False
        exclude = list(self.ids) if self.ids else []
        channel_rec = self._find_channel_record_by_phone(
            variants, exclude_ids=exclude
        )
        if (
            channel_rec
            and channel_rec._name == "crm.reception"
            and channel_rec.distribution_location_id
        ):
            return channel_rec.distribution_location_id.id
        return False

    @api.model
    def _duplicate_active_owner_write_vals(self, vals_or_phone, esp, esup, etl, status=False):
        write_vals = super()._duplicate_active_owner_write_vals(
            vals_or_phone, esp, esup, etl, status=status
        )
        if self._name != "crm.reception":
            return write_vals
        loc_id = self._reception_existing_visit_location(vals_or_phone)
        if not loc_id and len(self) == 1:
            loc_id = self._reception_existing_visit_location(
                {
                    "new_phone": self.new_phone or "",
                    "country_id": self.country_id.id if self.country_id else False,
                }
            )
        if loc_id:
            write_vals["distribution_location_id"] = loc_id
        return write_vals

    def _reception_use_location_for_assignment(self):
        """Location rotation for new walk-in leads only — not existing customers."""
        if self._name != "crm.reception":
            return False
        if self.env.context.get("lead_distribution_skip_assign"):
            return False
        if self.env.context.get("wing_skip_distribution_for_duplicate"):
            return False
        if self.env.context.get("quota_treat_as_new"):
            return bool(self._resolve_reception_location_id())
        if len(self) == 1:
            if self.existing_salesperson_id or (getattr(self, "status", None) or "").strip():
                return False
        return bool(self._resolve_reception_location_id())

    @api.model
    def _default_reception_location_id(self):
        loc = self.env.ref(
            "crm_distribution_location.distribution_location_head_office",
            raise_if_not_found=False,
        )
        return loc.id if loc else False

    def _resolve_reception_location_id(self, vals=None):
        """
        Location for reception walk-in assignment.

        On create, crm_custom_menu calls assign on an empty recordset — use context/vals/default.
        """
        if self._name != "crm.reception":
            return False
        if len(self) == 1 and self.distribution_location_id:
            return self.distribution_location_id.id
        if vals and vals.get("distribution_location_id"):
            return int(vals["distribution_location_id"])
        ctx_loc = self.env.context.get("distribution_location_id")
        if ctx_loc:
            return int(ctx_loc)
        if not self.env.context.get("lead_distribution_skip_assign"):
            return self._default_reception_location_id()
        return False

    def _walkin_location_id_for_filter(self):
        """Reception walk-in location for member filtering (strict — no global pool)."""
        return self._resolve_reception_location_id()

    def _walkin_members_at_location(self, loc_id):
        return self.env["crm.wing.member"].sudo().search(
            [
                ("type", "=", TYPE_WALKIN),
                ("active", "=", True),
                ("location_id", "=", loc_id),
            ],
            order="sequence asc",
        )

    def _walkin_users_at_location(self, loc_id):
        members = self._walkin_members_at_location(loc_id)
        users = members.mapped("user_id").filtered(
            lambda u: u and u.active and u != self.env.user
        )
        return members, users

    def _walkin_location_rotation_key(self, loc_id):
        return "crm_lead_distribution.walkin_last_user_loc_%s" % loc_id

    def _walkin_location_team_rotation_key(self, loc_id, wing):
        return "crm_lead_distribution.walkin_last_user_team_%s_loc_%s" % (
            wing.id,
            loc_id,
        )

    def _walkin_reception_lead_counts(self, loc_id, wing, users):
        """Sent reception leads per salesperson at wing + location."""
        counts = {uid: 0 for uid in users.ids}
        if not users or not loc_id or not wing:
            return counts
        groups = self.env["crm.reception"].sudo().read_group(
            [
                ("state_crm", "=", "sent"),
                ("distribution_location_id", "=", loc_id),
                ("assigned_sales_wing_id", "=", wing.id),
                ("assigned_salesperson_id", "in", users.ids),
            ],
            ["id:count"],
            ["assigned_salesperson_id"],
            lazy=False,
        )
        for group in groups:
            salesperson = group.get("assigned_salesperson_id")
            if not salesperson:
                continue
            counts[salesperson[0]] = group.get("id_count", 0)
        return counts

    def _walkin_users_at_min_count(self, loc_id, wing, members, users):
        """
        Only users with the fewest sent reception leads at this wing + location.
        Preserves Distribution Configuration sequence order.
        """
        counts = self._walkin_reception_lead_counts(loc_id, wing, users)
        min_count = min(counts.values()) if counts else 0
        tied_ids = {uid for uid, count in counts.items() if count == min_count}
        tied = self.env["res.users"]
        for member in members:
            user = member.user_id
            if user in users and user.id in tied_ids:
                tied |= user
        if not tied:
            tied = users
        _logger.info(
            "Lead distribution [location] wing=%s loc_id=%s min_count=%s "
            "eligible=%s counts=%s",
            wing.name if wing else "?",
            loc_id,
            min_count,
            ", ".join(tied.mapped("name")),
            ", ".join(
                "%s=%s" % (users.browse(uid).name, count)
                for uid, count in sorted(counts.items(), key=lambda item: item[1])
            ),
        )
        return tied, min_count

    def _pick_walkin_user_by_min_count_rotation(self, loc_id, wing, members, users):
        """Rotate only among users tied for lowest lead count at wing + location."""
        eligible, min_count = self._walkin_users_at_min_count(
            loc_id, wing, members, users
        )
        key = self._walkin_location_team_rotation_key(loc_id, wing)
        last_id = int(
            self.env["ir.config_parameter"].sudo().get_param(key, "0") or 0
        )
        last_user = self.env["res.users"].browse(last_id).exists()
        if last_user and last_user not in eligible:
            next_user = eligible[0]
            rotation_reason = (
                "lowest count (%s) — last user not eligible, start from first"
                % min_count
            )
        elif not last_user:
            next_user = eligible[0]
            rotation_reason = "lowest count (%s) — first eligible user" % min_count
        else:
            idx = eligible.ids.index(last_user.id)
            next_user = eligible[(idx + 1) % len(eligible)]
            rotation_reason = (
                "lowest count (%s) — next after %s"
                % (min_count, last_user.name)
            )
        return next_user, rotation_reason

    def _revert_walkin_location_rotation(self, loc_id, failed_user):
        members, member_users = self._walkin_users_at_location(loc_id)
        if failed_user not in member_users:
            return
        idx = member_users.ids.index(failed_user.id)
        prev_user = member_users[(idx - 1) % len(member_users)]
        self.env["ir.config_parameter"].sudo().set_param(
            self._walkin_location_rotation_key(loc_id),
            str(prev_user.id),
        )
        _logger.info(
            "Lead distribution: location rotation reverted to %s (SMS failed for %s)",
            prev_user.name,
            failed_user.name,
        )

    def _commit_walkin_location_rotation(self, loc_id, user):
        """After SMS succeeds, last served at this location = user who got the lead."""
        if not loc_id or not user:
            return
        members, member_users = self._walkin_users_at_location(loc_id)
        if user not in member_users:
            return
        self.env["ir.config_parameter"].sudo().set_param(
            self._walkin_location_rotation_key(loc_id),
            str(user.id),
        )
        _logger.info(
            "Lead distribution: location rotation committed to %s (loc_id=%s)",
            user.name,
            loc_id,
        )

    def _next_walkin_user_for_sms_retry(self, loc_id, after_user):
        members, member_users = self._walkin_users_at_location(loc_id)
        if not member_users or not after_user:
            return self.env["res.users"], False
        dist = self.env["crm.lead.distribution"]
        start = 0
        if after_user in member_users:
            start = member_users.ids.index(after_user.id) + 1
        for i in range(len(member_users)):
            candidate = member_users[(start + i) % len(member_users)]
            if candidate == after_user:
                continue
            can_sms = (
                dist._is_eligible_for_sms(candidate)
                if hasattr(dist, "_is_eligible_for_sms")
                else bool(dist._contact_from_login_only(candidate)[0])
            )
            if not can_sms:
                continue
            member = members.filtered(lambda m: m.user_id == candidate)[:1]
            wing = member.team_id if member else False
            _logger.info(
                "Lead distribution: walk-in SMS retry location=%s -> %s",
                loc_id,
                candidate.name,
            )
            return candidate, wing
        return self.env["res.users"], False

    def _pick_walkin_user_at_location(self, loc_id, after_user=None):
        members, users = self._walkin_users_at_location(loc_id)
        if not users:
            return self.env["res.users"], False
        if after_user and after_user in users:
            idx = users.ids.index(after_user.id)
            next_user = users[(idx + 1) % len(users)]
        else:
            key = self._walkin_location_rotation_key(loc_id)
            last_id = int(
                self.env["ir.config_parameter"].sudo().get_param(key, "0") or 0
            )
            last_user = self.env["res.users"].browse(last_id).exists()
            if last_user not in users:
                next_user = users[0]
            else:
                idx = users.ids.index(last_user.id)
                next_user = users[(idx + 1) % len(users)]
        self.env["ir.config_parameter"].sudo().set_param(
            self._walkin_location_rotation_key(loc_id),
            str(next_user.id),
        )
        member = members.filtered(lambda m: m.user_id == next_user)[:1]
        wing = member.team_id if member else False
        return next_user, wing

    def _auto_assign_walkin_by_location(self, loc_id):
        user, wing = self._pick_walkin_user_at_location(loc_id)
        if not user:
            self._validation_error_no_active_users(TYPE_WALKIN)
        loc_name = (
            self.env["property.distribution.location"].browse(loc_id).name or loc_id
        )
        _logger.info(
            "Lead distribution [location] %s -> user=%s wing=%s",
            loc_name,
            user.name,
            wing.name if wing else None,
        )
        return user, wing

    def _auto_assign_walkin_by_team_location(self, loc_id):
        """Quota chooses wing; fairness + last user memory are isolated per team + location."""
        stype = TYPE_WALKIN
        Quota = self.env["crm.lead.quota"].sudo()

        teams = Quota.search([("type", "=", stype), ("active", "=", True)])
        active_users = self._active_distribution_users(stype)
        if not teams or not active_users:
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
            self._validation_error_no_active_users(stype)

        self._log_quota_ratio_audit(stype, teams, candidates, quota_reset)
        highest_ratio = max(self._get_ratio(t) for t in candidates)
        top_teams = candidates.filtered(lambda t: self._get_ratio(t) == highest_ratio)
        selected = sorted(top_teams, key=lambda t: (t.assigned_count, t.id))[0]
        wing = selected.team_id

        members = self.env["crm.wing.member"].sudo().search(
            self._distribution_member_domain(stype, wing),
            order="sequence asc",
        )
        users = members.mapped("user_id").filtered(
            lambda u: u and u.active and u != self.env.user
        )
        if not users:
            self._validation_error_no_active_users(stype)

        next_user, rotation_reason = self._pick_walkin_user_by_min_count_rotation(
            loc_id, wing, members, users
        )
        _logger.info("Lead distribution [rotation] pick reason: %s", rotation_reason)
        selected.sudo().write(
            {"assigned_count": (selected.assigned_count or 0) + 1}
        )
        key = self._walkin_location_team_rotation_key(loc_id, wing)
        self.env["ir.config_parameter"].sudo().set_param(key, str(next_user.id))
        self.env["ir.config_parameter"].sudo().set_param(
            "crm_lead_distribution.last_wing_%s" % stype, str(wing.id)
        )
        _logger.info(
            "Lead distribution [location] loc_id=%s wing=%s user=%s quota_id=%s "
            "assigned_count now=%s",
            loc_id,
            wing.name,
            next_user.name,
            selected.id,
            selected.assigned_count,
        )
        return next_user, wing

    def _apply_wing_after_assign(self, records):
        """Sync sales wing from location-filtered member row after quota assign."""
        for rec in records.filtered(
            lambda r: r._name == "crm.reception"
            and r.nominated_salesperson_id
            and r._reception_should_assign_by_location()
        ):
            loc_id = rec._resolve_reception_location_id()
            if not loc_id:
                continue
            members, users = rec._walkin_users_at_location(loc_id)
            if rec.nominated_salesperson_id not in users:
                _logger.error(
                    "Lead distribution [location] user %s not at loc_id=%s — re-assign",
                    rec.nominated_salesperson_id.name,
                    loc_id,
                )
                user, wing = rec.with_context(
                    distribution_location_id=loc_id
                ).auto_assign_lead(TYPE_WALKIN)
                if user:
                    rec._write_nominated_wing_fields(user, wing)
                continue
            if rec.nominated_sales_wing_id:
                continue
            member = members.filtered(
                lambda m: m.user_id == rec.nominated_salesperson_id
            )[:1]
            if member and member.team_id:
                rec._write_nominated_wing_fields(
                    rec.nominated_salesperson_id, member.team_id
                )
        return super()._apply_wing_after_assign(records)

    def auto_assign_lead(self, source_type=None):
        stype = source_type or self._distribution_type()
        if (
            self._name == "crm.reception"
            and stype == TYPE_WALKIN
            and not self.env.context.get("lead_distribution_skip_assign")
        ):
            if (
                len(self) == 1
                and not self.env.context.get("quota_treat_as_new")
                and (
                    self.existing_salesperson_id
                    or (getattr(self, "status", None) or "").strip()
                )
            ):
                return super().auto_assign_lead(source_type)
            loc_id = self._resolve_reception_location_id()
            if not loc_id:
                raise ValidationError(
                    _(
                        "Please select a Location for this walk-in lead. "
                        "Assignment uses only Distribution Members at that location."
                    )
                )
            return self.with_context(
                distribution_location_id=loc_id
            )._auto_assign_walkin_by_team_location(loc_id)
        return super().auto_assign_lead(source_type)

    def _create_bypass_wing(self, vals, extra_ctx=None):
        ctx = dict(extra_ctx or {})
        vals = dict(vals)
        if (
            self._name == "crm.reception"
            and not ctx.get("lead_distribution_skip_assign")
        ):
            loc_id = (
                vals.get("distribution_location_id")
                or ctx.get("distribution_location_id")
                or self._default_reception_location_id()
            )
            if loc_id:
                vals["distribution_location_id"] = loc_id
                ctx["distribution_location_id"] = loc_id
        return super()._create_bypass_wing(vals, extra_ctx=ctx or None)

    def _distribution_member_domain(self, stype, wing=None):
        domain = super()._distribution_member_domain(stype, wing)
        if (
            stype != TYPE_WALKIN
            or self._name != "crm.reception"
            or not self._reception_use_location_for_assignment()
        ):
            return domain
        loc_id = self._walkin_location_id_for_filter()
        if loc_id:
            domain.append(("location_id", "=", loc_id))
            loc_name = ""
            if len(self) == 1 and self.distribution_location_id:
                loc_name = self.distribution_location_id.name
            elif loc_id:
                loc_name = (
                    self.env["property.distribution.location"]
                    .browse(loc_id)
                    .name
                    or ""
                )
            _logger.info(
                "Lead distribution [location] walk-in filter location_id=%s (%s)",
                loc_id,
                loc_name,
            )
        return domain

    def _validation_error_no_active_users(self, stype):
        loc_id = self._walkin_location_id_for_filter()
        if stype == TYPE_WALKIN and self._name == "crm.reception" and loc_id:
            loc = self.env["property.distribution.location"].browse(loc_id)
            members_n = self.env["crm.wing.member"].sudo().search_count(
                [
                    ("type", "=", stype),
                    ("active", "=", True),
                    ("location_id", "=", loc_id),
                ]
            )
            if not members_n:
                raise ValidationError(
                    _(
                        "No active Distribution Configuration member for walk-in "
                        "at location “%(location)s”.\n\n"
                        "Add members under Property → Configuration → "
                        "Lead Distribution → Distribution Configuration with "
                        "Location = %(location)s."
                    )
                    % {"location": loc.name}
                )
        return super()._validation_error_no_active_users(stype)
