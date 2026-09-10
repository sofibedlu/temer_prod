# -*- coding: utf-8 -*-
import inspect
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# wing.distribution.type code/name -> crm.wing.member type
WING_TYPE_TO_QUOTA = {
    "walk_in": "walkin",
    "walkin": "walkin",
    "walk in": "walkin",
    "website": "website",
    "6033": "call_center",
    "call_center": "call_center",
    "call center": "call_center",
}
# Wing export labels we never import (checked before any DB access).
IMPORT_SKIP_TYPE_LABELS = frozenset(
    {
        "affiliate",
        "referral",
    }
)


class CrmWingMember(models.Model):
    _name = "crm.wing.member"
    _description = "CRM Wing Member"
    _order = "sequence asc"

    team_id = fields.Many2one(
        "property.sales.wing",
        string="Team",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
    )
    type = fields.Selection(
        selection=[
            ("walkin", "Walkin"),
            ("call_center", "Call Center"),
            ("website", "Website"),
        ],
        string="Type",
        required=True,
    )
    sequence = fields.Integer(string="Sequence", readonly=True, copy=False)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        (
            "unique_user_team_type",
            "unique(team_id, user_id, type)",
            "This user is already assigned to this Team and Type.",
        ),
    ]

    @api.model
    def _get_team_for_user(self, user):
        if not user:
            return self.env["property.sales.wing"]
        if isinstance(user, int):
            user = self.env["res.users"].browse(user)
        Wing = self.env["property.sales.wing"]

        mapping = self.env["property.salesperson.mapping"].search(
            [("user_id", "=", user.id)], limit=1
        )
        if mapping and mapping.supervisor_id:
            team = self.env["property.sales.team"].search(
                [("supervisor_ids", "in", mapping.supervisor_id.id)], limit=1
            )
            if team:
                wing = Wing.search([("team_ids", "in", team.id)], limit=1)
                if wing:
                    return wing

        sup_rec = self.env["property.sales.supervisor"].search(
            [("name", "=", user.id)], limit=1
        )
        if sup_rec and sup_rec.sales_team_id:
            return sup_rec.sales_team_id.wing_id

        team = self.env["property.sales.team"].search(
            [("manager_id", "=", user.id)], limit=1
        )
        if team:
            return Wing.search([("team_ids", "in", team.id)], limit=1)

        return Wing.search([("manager_id", "=", user.id)], limit=1)

    def _apply_team_from_user(self, vals):
        if vals.get("user_id"):
            wing = self._get_team_for_user(vals["user_id"])
            if wing:
                vals["team_id"] = wing.id

    @api.onchange("user_id")
    def _onchange_user_id_set_team(self):
        """Editable list: fill Team as soon as User is chosen (before Save)."""
        if self.user_id:
            self.team_id = self._get_team_for_user(self.user_id)
        else:
            self.team_id = False

    @api.model_create_multi
    def create(self, vals_list):
        bulk_import = self.env.context.get("wing_distribution_import")
        cleaned = []
        for vals in vals_list:
            vals = dict(vals)
            if not bulk_import:
                self._apply_team_from_user(vals)
            if not vals.get("user_id"):
                raise ValidationError(_("User is required."))
            if not vals.get("type"):
                raise ValidationError(_("Type is required."))
            if not vals.get("team_id"):
                raise ValidationError(
                    _("Team is required. Check salesperson mapping.")
                )
            if not vals.get("sequence"):
                if bulk_import:
                    vals["sequence"] = 0
                else:
                    last = self.search(
                        [
                            ("team_id", "=", vals["team_id"]),
                            ("type", "=", vals["type"]),
                        ],
                        order="sequence desc",
                        limit=1,
                    )
                    vals["sequence"] = (last.sequence + 1) if last else 1
            cleaned.append(vals)
        return super().create(cleaned)

    def write(self, vals):
        if vals.get("user_id"):
            wing = self._get_team_for_user(vals["user_id"])
            vals["team_id"] = wing.id if wing else False
        return super().write(vals)

    @api.constrains("user_id", "team_id")
    def _check_team_for_user(self):
        for rec in self:
            if rec.user_id and not rec.team_id:
                raise ValidationError(
                    _(
                        "No team found for %(name)s. "
                        "Assign them under Property salesperson mapping first."
                    )
                    % {"name": rec.user_id.name}
                )

    _IMPORT_DROP_FIELDS = frozenset({"team_id", "wing_id", "sequence", "status"})
    _WING_IMPORT_CREATE_BATCH = 200

    @api.model
    def _import_field_base(self, field_path):
        if not field_path:
            return ""
        return field_path.split("/")[0].split(".")[0]

    @api.model
    def _map_wing_distribution_type_to_quota(self, wing_type):
        """Map wing.distribution.type to crm.wing.member channel type."""
        if not wing_type:
            return False
        for key in (
            (wing_type.code or "").strip().lower(),
            (wing_type.name or "").strip().lower(),
        ):
            if key in WING_TYPE_TO_QUOTA:
                return WING_TYPE_TO_QUOTA[key]
        return False

    @api.model
    def _is_affiliate_type_label(self, type_label):
        key = (type_label or "").strip().lower()
        if not key:
            return False
        if key in IMPORT_SKIP_TYPE_LABELS or key.startswith("affiliate"):
            return True
        return key == "referral"

    @api.model
    def _build_user_import_index(self):
        """name/login (lower) -> user id for fast import (no per-row search)."""
        self.env.cr.execute(
            """
            SELECT u.id, u.login, COALESCE(p.name, '')
            FROM res_users u
            JOIN res_partner p ON p.id = u.partner_id
            WHERE u.active IS NOT FALSE
            """
        )
        index = {}
        for uid, login, name in self.env.cr.fetchall():
            for key in (name, login):
                if key:
                    norm = key.strip().lower()
                    if norm not in index:
                        index[norm] = uid
        return index

    @api.model
    def _build_team_for_user_index(self):
        """user_id -> wing id; built once per import (not per spreadsheet row)."""
        index = {}
        Wing = self.env["property.sales.wing"].sudo()
        Mapping = self.env["property.salesperson.mapping"].sudo()
        SalesTeam = self.env["property.sales.team"].sudo()

        for mapping in Mapping.search([("user_id", "!=", False)]):
            uid = mapping.user_id.id
            if uid in index or not mapping.supervisor_id:
                continue
            team = SalesTeam.search(
                [("supervisor_ids", "in", mapping.supervisor_id.id)], limit=1
            )
            if team:
                wing = Wing.search([("team_ids", "in", team.id)], limit=1)
                if wing:
                    index[uid] = wing.id

        for sup in self.env["property.sales.supervisor"].sudo().search([]):
            uid = sup.name.id if sup.name else False
            if (
                uid
                and uid not in index
                and sup.sales_team_id
                and sup.sales_team_id.wing_id
            ):
                index[uid] = sup.sales_team_id.wing_id.id

        for team in SalesTeam.search([("manager_id", "!=", False)]):
            uid = team.manager_id.id
            if uid not in index:
                wing = Wing.search([("team_ids", "in", team.id)], limit=1)
                if wing:
                    index[uid] = wing.id

        for wing in Wing.search([("manager_id", "!=", False)]):
            uid = wing.manager_id.id
            if uid not in index:
                index[uid] = wing.id
        return index

    @api.model
    def _fetch_existing_member_keys(self):
        self.env.cr.execute(
            "SELECT team_id, user_id, type FROM crm_wing_member"
        )
        return {tuple(row) for row in self.env.cr.fetchall()}

    @api.model
    def _build_wing_type_import_index(self):
        """distribution type label (lower) -> quota type code."""
        index = {}
        for wt in self.env["wing.distribution.type"].sudo().search([]):
            quota = self._map_wing_distribution_type_to_quota(wt)
            if not quota:
                continue
            for key in (wt.name, wt.code):
                if key:
                    index[key.strip().lower()] = quota
        return index

    @api.model
    def _resolve_user_for_import(self, name, user_index=None):
        """Match Wing export user name to res.users (skip row if not found)."""
        name = (name or "").strip()
        if not name:
            return self.env["res.users"]
        if user_index is not None:
            uid = user_index.get(name.lower())
            if uid:
                return self.env["res.users"].browse(uid)
            return self.env["res.users"]
        Users = self.env["res.users"].sudo()
        for domain in (
            [("name", "=", name)],
            [("name", "ilike", name)],
            [("login", "=", name)],
        ):
            user = Users.search(domain, limit=1)
            if user:
                return user
        return Users

    @api.model
    def _resolve_quota_type_from_label(self, type_label, wing_type_index=None):
        key = (type_label or "").strip().lower()
        if self._is_affiliate_type_label(type_label):
            return False
        if key in WING_TYPE_TO_QUOTA:
            return WING_TYPE_TO_QUOTA[key]
        if wing_type_index is not None:
            return wing_type_index.get(key, False)
        WingType = self.env["wing.distribution.type"].sudo()
        wt = WingType.search([("name", "=", type_label)], limit=1)
        if not wt:
            wt = WingType.search([("name", "ilike", type_label)], limit=1)
        return self._map_wing_distribution_type_to_quota(wt) if wt else False

    @api.model
    def _prepare_wing_distribution_import(self, fields, data):
        """
        Wing export → standard Odoo import on Distribution Configuration.
        Map User + Distribution Types + Active only; team and sequence are automatic.
        """
        stats = {
            "skipped_affiliate": 0,
            "skipped_user": 0,
            "skipped_type": 0,
            "skipped_team": 0,
            "skipped_duplicate": 0,
        }
        if not fields:
            return fields, data, stats

        mapped_bases = {self._import_field_base(f) for f in fields}
        if "type" not in mapped_bases:
            raise ValidationError(
                _(
                    "Map the Excel column «Distribution Types» to the Odoo field "
                    "«Type». Wing and Status must stay unmapped."
                )
            )

        keep_idx = []
        new_fields = []
        for i, field_path in enumerate(fields):
            base = self._import_field_base(field_path)
            if base in self._IMPORT_DROP_FIELDS:
                continue
            keep_idx.append(i)
            if base == "user_id":
                new_fields.append("user_id/.id")
            else:
                new_fields.append(field_path)

        type_idx = next(
            (
                j
                for j, f in enumerate(new_fields)
                if self._import_field_base(f) == "type"
            ),
            None,
        )
        active_idx = next(
            (
                j
                for j, f in enumerate(new_fields)
                if self._import_field_base(f) == "active"
            ),
            None,
        )
        user_idx = next(
            (
                j
                for j, f in enumerate(new_fields)
                if self._import_field_base(f) == "user_id"
            ),
            None,
        )
        if not any(self._import_field_base(f) == "team_id" for f in new_fields):
            new_fields.append("team_id/.id")
        team_idx = next(
            j
            for j, f in enumerate(new_fields)
            if self._import_field_base(f) == "team_id"
        )

        user_index = self._build_user_import_index()
        wing_type_index = self._build_wing_type_import_index()
        team_index = self._build_team_for_user_index()
        existing_keys = self._fetch_existing_member_keys()
        seen_keys = set()
        new_data = []
        for row in data:
            cells = [row[i] if i < len(row) else "" for i in keep_idx]
            while len(cells) < len(new_fields):
                cells.append("")

            if type_idx is not None:
                raw_type = cells[type_idx]
                if self._is_affiliate_type_label(raw_type):
                    stats["skipped_affiliate"] += 1
                    continue
                quota_type = self._resolve_quota_type_from_label(
                    raw_type, wing_type_index=wing_type_index
                )
                if not quota_type:
                    stats["skipped_type"] += 1
                    continue
                cells[type_idx] = quota_type
            else:
                quota_type = False

            user = self.env["res.users"]
            if user_idx is not None:
                user = self._resolve_user_for_import(
                    cells[user_idx], user_index=user_index
                )
                if not user:
                    stats["skipped_user"] += 1
                    continue
                cells[user_idx] = str(user.id)

            uid = user.id if user else 0
            wing_id = team_index.get(uid)
            if not wing_id:
                stats["skipped_team"] += 1
                continue
            cells[team_idx] = str(wing_id)

            row_key = (wing_id, uid, quota_type)
            if row_key in seen_keys or row_key in existing_keys:
                stats["skipped_duplicate"] += 1
                continue
            seen_keys.add(row_key)

            if active_idx is not None:
                active_val = str(cells[active_idx] or "").strip().lower()
                cells[active_idx] = (
                    "1" if active_val in ("1", "true", "yes", "y") else "0"
                )
            new_data.append(cells)
        return new_fields, new_data, stats

    @api.model
    def _wing_import_skip_messages(self, stats):
        skipped = sum(stats.values())
        if not skipped:
            return []
        parts = []
        if stats["skipped_affiliate"]:
            parts.append(
                _("%(n)s: Affiliate (excluded)") % {"n": stats["skipped_affiliate"]}
            )
        if stats["skipped_user"]:
            parts.append(_("%(n)s: user not found") % {"n": stats["skipped_user"]})
        if stats["skipped_type"]:
            parts.append(_("%(n)s: unsupported type") % {"n": stats["skipped_type"]})
        if stats["skipped_team"]:
            parts.append(
                _("%(n)s: no team — set Property salesperson mapping first")
                % {"n": stats["skipped_team"]}
            )
        if stats["skipped_duplicate"]:
            parts.append(
                _("%(n)s: already in Distribution Configuration")
                % {"n": stats["skipped_duplicate"]}
            )
        return [
            {
                "type": "warning",
                "message": _("Skipped %(total)s row(s): %(detail)s")
                % {"total": skipped, "detail": "; ".join(parts)},
            }
        ]

    @api.model
    def _wing_import_is_dryrun(self):
        """True when import UI clicked Test (no DB writes needed)."""
        if self.env.context.get("wing_import_dryrun"):
            return True
        for frame_info in inspect.stack()[1:]:
            if frame_info.function != "execute_import":
                continue
            return bool(frame_info.frame.f_locals.get("dryrun"))
        return False

    @api.model
    def _wing_import_rows_to_vals(self, fields, data):
        col = {self._import_field_base(f): i for i, f in enumerate(fields)}
        vals_list = []
        for row in data:
            vals = {
                "user_id": int(row[col["user_id"]]),
                "team_id": int(row[col["team_id"]]),
                "type": row[col["type"]],
                "sequence": 0,
            }
            if "active" in col:
                active_val = str(row[col["active"]] or "").strip().lower()
                vals["active"] = active_val in ("1", "true", "yes", "y")
            vals_list.append(vals)
        return vals_list

    @api.model
    def load(self, fields, data):
        if not self.env.context.get("import_file"):
            return super().load(fields, data)

        fields, data, stats = self._prepare_wing_distribution_import(fields, data)
        messages = self._wing_import_skip_messages(stats)
        skipped = sum(stats.values())

        if not data:
            _logger.info(
                "wing distribution import: nothing to create (%s row(s) skipped)",
                skipped,
            )
            return {"ids": [], "messages": messages, "nextrow": 0}

        vals_list = self._wing_import_rows_to_vals(fields, data)
        count = len(vals_list)

        if self._wing_import_is_dryrun():
            _logger.info(
                "wing distribution import (test): would create %d, skipped %d",
                count,
                skipped,
            )
            messages.append(
                {
                    "type": "info",
                    "message": _("Test OK: %(count)s row(s) would be imported.")
                    % {"count": count},
                }
            )
            return {"ids": [], "messages": messages, "nextrow": 0}

        _logger.info(
            "wing distribution import: creating %d record(s), skipped %d row(s)",
            count,
            skipped,
        )
        create_ctx = {
            "wing_distribution_import": True,
            "mail_create_nolog": True,
            "mail_notrack": True,
            "tracking_disable": True,
        }
        Creator = self.with_context(**create_ctx)
        records = self.env["crm.wing.member"]
        try:
            batch_size = self._WING_IMPORT_CREATE_BATCH
            for offset in range(0, count, batch_size):
                batch = vals_list[offset : offset + batch_size]
                records |= Creator.create(batch)
        except ValidationError as err:
            return {
                "ids": False,
                "messages": messages + [{"type": "error", "message": str(err)}],
            }

        self._renumber_sequences_for_members(records)
        _logger.info("wing distribution import: done, %d created", len(records))
        return {"ids": records.ids, "messages": messages, "nextrow": 0}

    @api.model
    def _renumber_sequences_for_members(self, imported):
        """Renumber 1..n only for team+type groups touched by this import."""
        if not imported:
            return 0
        groups = {(rec.team_id.id, rec.type) for rec in imported if rec.team_id}
        for team_id, stype in groups:
            self.env.cr.execute(
                """
                WITH ranked AS (
                    SELECT id,
                           ROW_NUMBER() OVER (ORDER BY sequence, id) AS new_seq
                    FROM crm_wing_member
                    WHERE team_id = %s AND type = %s
                )
                UPDATE crm_wing_member AS m
                SET sequence = r.new_seq
                FROM ranked AS r
                WHERE m.id = r.id
                  AND m.sequence IS DISTINCT FROM r.new_seq
                """,
                (team_id, stype),
            )
        imported.invalidate_recordset(["sequence"])
        return len(groups)

    @api.model
    def renumber_all_sequences(self):
        """Set sequence 1..n per Team + Type (order: sequence, id)."""
        members = self.with_context(active_test=False).search(
            [], order="team_id, type, sequence, id"
        )
        counters = {}
        for rec in members:
            key = (rec.team_id.id, rec.type)
            counters[key] = counters.get(key, 0) + 1
            new_seq = counters[key]
            if rec.sequence != new_seq:
                rec.sequence = new_seq
        return len(members)
