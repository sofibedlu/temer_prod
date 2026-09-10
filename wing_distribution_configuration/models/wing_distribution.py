# -*- coding: utf-8 -*-

import logging
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WingDistributionRound(models.Model):
    _name = "wing.distribution.round"
    _description = "Wing Distribution Round"
    _order = "id desc"

    name = fields.Char(string="Round Name", required=True)
    distribution_type_id = fields.Many2one(
        "wing.distribution.type", string="Distribution Type", required=True, ondelete="cascade"
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("started", "Started"),
            ("served", "Served"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    date_started = fields.Datetime(string="Started At", readonly=True)
    date_served = fields.Datetime(string="Finished At", readonly=True)


class WingDistributionType(models.Model):
    _name = "wing.distribution.type"
    _description = "Wing Distribution Type"
    _rec_name = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Distribution type code must be unique."),
    ]


class WingDistributionLine(models.Model):
    _name = "wing.distribution.line"
    _description = "Wing Distribution Line"
    _order = "team_id, user_id"

    user_id = fields.Many2one("res.users", string="User", required=True)
    team_id = fields.Many2one(
        "property.sales.team",
        string="Team",
        compute="_compute_team_id",
        store=True,
        readonly=True,
    )
    wing_id = fields.Many2one(
        "property.sales.wing",
        string="Wing",
        compute="_compute_wing_id",
        store=True,
        readonly=True,
    )
    distribution_type_ids = fields.Many2many(
        "wing.distribution.type",
        "wing_distribution_line_type_rel",
        "line_id",
        "type_id",
        string="Distribution Types",
        required=True,
        help="Select one or more types. Each type creates a separate row on save. Same user cannot have same type twice.",
    )
    round_id = fields.Many2one(
        "wing.distribution.round",
        string="Round",
        readonly=True,
        help="Round this line participates in (set when round starts). New registrations during a round are not included until next round.",
    )
    status = fields.Selection(
        [
            ("new", "New"),
            ("served", "Served"),
        ],
        string="Status",
        default="new",
        help="New = newly registered (counted in next round). Served = served in current round. Empty = not yet served this round.",
    )
    active = fields.Boolean(default=True)
    user_domain_ids = fields.Many2many(
        "res.users",
        compute="_compute_user_domain_ids",
        string="User Domain",
        store=False,
    )
    # Types this user already has (other lines); used to hide them from Distribution Type dropdown
    type_ids_already_used_by_user = fields.Many2many(
        "wing.distribution.type",
        compute="_compute_type_ids_already_used_by_user",
        string="Types already used",
        store=False,
    )

    _sql_constraints = []

    def _get_team_for_user_batch(self, users):
        """Batch resolve team for many users. Returns dict user_id -> team record (or False)."""
        if not users:
            return {}
        user_ids = users.ids
        res = {uid: False for uid in user_ids}
        # Supervisors: name in user_ids
        supervisors = self.env["property.sales.supervisor"].search([("name", "in", user_ids)])
        for sup in supervisors:
            if sup.sales_team_id:
                res[sup.name.id] = sup.sales_team_id
            elif sup.id:
                team = self.env["property.sales.team"].search(
                    [("supervisor_ids", "in", sup.id)], limit=1
                )
                if team:
                    res[sup.name.id] = team
        # Mappings: user_id in user_ids, then team via supervisor
        mappings = self.env["property.salesperson.mapping"].search([("user_id", "in", user_ids)])
        for m in mappings:
            if res.get(m.user_id.id):
                continue
            if m.supervisor_id:
                team = self.env["property.sales.team"].search(
                    [("supervisor_ids", "in", m.supervisor_id.id)], limit=1
                )
                if team:
                    res[m.user_id.id] = team
        return res

    def _get_wing_for_user_batch(self, users, team_by_user=None):
        """Batch resolve wing for many users. Returns dict user_id -> wing record (or False)."""
        if not users:
            return {}
        user_ids = users.ids
        res = {uid: False for uid in user_ids}
        if team_by_user is None:
            team_by_user = self._get_team_for_user_batch(users)
        # Wing managers
        wings = self.env["property.sales.wing"].search([("manager_id", "in", user_ids)])
        for w in wings:
            res[w.manager_id.id] = w
        # Sales managers -> team -> wing (one search for all wings by team)
        teams_as_manager = self.env["property.sales.team"].search([("manager_id", "in", user_ids)])
        if teams_as_manager:
            wings_for_teams = self.env["property.sales.wing"].search(
                [("team_ids", "in", teams_as_manager.ids)]
            )
            team_to_wing = {}
            for w in wings_for_teams:
                for tid in w.team_ids.ids:
                    if tid not in team_to_wing:
                        team_to_wing[tid] = w
            for t in teams_as_manager:
                if res.get(t.manager_id.id):
                    continue
                w = team_to_wing.get(t.id)
                if w:
                    res[t.manager_id.id] = w
        # Supervisor path: supervisor.sales_team_id.wing_id
        supervisors = self.env["property.sales.supervisor"].search([("name", "in", user_ids)])
        for sup in supervisors:
            if res.get(sup.name.id):
                continue
            if sup.sales_team_id and sup.sales_team_id.wing_id:
                res[sup.name.id] = sup.sales_team_id.wing_id
        # Team -> wing for remaining (one search)
        need_wing = [uid for uid in user_ids if not res.get(uid) and team_by_user.get(uid)]
        team_ids = list({team_by_user[uid].id for uid in need_wing if team_by_user.get(uid)})
        if need_wing and team_ids:
            wings_team = self.env["property.sales.wing"].search(
                [("team_ids", "in", team_ids)]
            )
            team_to_wing = {}
            for w in wings_team:
                for tid in w.team_ids.ids:
                    if tid not in team_to_wing:
                        team_to_wing[tid] = w
            for uid in need_wing:
                team = team_by_user.get(uid)
                if team:
                    w = team_to_wing.get(team.id)
                    if w:
                        res[uid] = w
        return res

    @api.depends("user_id")
    def _compute_team_id(self):
        users = self.mapped("user_id")
        team_by_user = self._get_team_for_user_batch(users) if users else {}
        for rec in self:
            rec.team_id = team_by_user.get(rec.user_id.id, False) if rec.user_id else False

    @api.depends("user_id")
    def _compute_wing_id(self):
        users = self.mapped("user_id")
        if not users:
            for rec in self:
                rec.wing_id = False
            return
        team_by_user = self._get_team_for_user_batch(users)
        wing_by_user = self._get_wing_for_user_batch(users, team_by_user=team_by_user)
        for rec in self:
            rec.wing_id = wing_by_user.get(rec.user_id.id, False) if rec.user_id else False

    @api.constrains("user_id", "distribution_type_ids")
    def _check_user_type_unique(self):
        """Same user (by integer ID) cannot have the same type in two different rows."""
        for rec in self:
            if not rec.user_id or not rec.distribution_type_ids:
                continue
            uid = rec.user_id.id
            if not isinstance(uid, int):
                continue
            for t in rec.distribution_type_ids:
                other = self.search(
                    [
                        ("user_id", "=", uid),
                        ("distribution_type_ids", "in", [t.id]),
                        ("id", "!=", rec.id),
                    ],
                    limit=1,
                )
                if other:
                    raise ValidationError(
                        _(
                            "User %(user)s already has type %(type)s. "
                            "Remove the existing line or choose another type."
                        )
                        % {"user": rec.user_id.name, "type": t.name}
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Expand: when multiple types selected, create one row per type."""
        if not vals_list:
            return self.env["wing.distribution.line"]
        expanded = []
        for vals in vals_list:
            type_ids = self._extract_type_ids(vals.get("distribution_type_ids"))
            if not type_ids:
                expanded.append(vals)
                continue
            base = {k: v for k, v in vals.items() if k != "distribution_type_ids"}
            for tid in type_ids:
                if "status" not in base:
                    base["status"] = "new"
                expanded.append({**base, "distribution_type_ids": [(6, 0, [tid])]})
        lines = super(WingDistributionLine, self).create(expanded)
        if len(lines) > 1:
            try:
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id,
                    "wing_distribution_multi_created",
                    {"count": len(lines)},
                )
            except Exception:
                pass
        # New lines should show status "New" so they are counted in the next round.
        return lines

    def _extract_type_ids(self, cmd):
        """Extract type ids from Odoo command (6,0,ids), (4,id), or plain list [id1, id2]."""
        ids = []
        if not cmd:
            return ids
        if hasattr(cmd, "ids"):
            return list(cmd.ids)
        if isinstance(cmd, int):
            return [cmd]
        if isinstance(cmd, (list, tuple)):
            for c in cmd:
                if isinstance(c, (list, tuple)):
                    if len(c) >= 3 and c[0] == 6:
                        ids.extend(c[2] if isinstance(c[2], (list, tuple)) else [c[2]])
                    elif len(c) >= 2 and c[0] == 4:
                        ids.append(c[1])
                    elif len(c) >= 1 and c[0] in (3, 5):
                        # (3, id) remove; (5) clear-all → handled in _apply_m2m_commands()
                        continue
                    elif all(isinstance(x, int) for x in c):
                        ids.extend(c)
                elif isinstance(c, int):
                    ids.append(c)
        return ids

    def _apply_m2m_commands(self, current_ids, commands):
        """
        Apply Odoo M2M commands to a list of ids and return resulting ids.
        """
        if commands is None:
            return list(current_ids or [])
        if hasattr(commands, "ids"):
            return list(commands.ids)
        if isinstance(commands, (list, tuple)) and all(isinstance(x, int) for x in commands):
            return list(commands)
        ids = set(current_ids or [])
        if isinstance(commands, (list, tuple)):
            for cmd in commands:
                if not isinstance(cmd, (list, tuple)) or not cmd:
                    continue
                op = cmd[0]
                if op == 6 and len(cmd) >= 3:
                    ids = set(cmd[2] or [])
                elif op == 5:
                    ids = set()
                elif op == 4 and len(cmd) >= 2:
                    ids.add(cmd[1])
                elif op == 3 and len(cmd) >= 2:
                    ids.discard(cmd[1])
                elif op == 0:
                    # (0, 0, values) create-linked record; id not known here
                    continue
        return list(ids)

    def init(self):
        """
        Data integrity: ensure exactly ONE row per (user, type).
        1. Split rows with many types into one row per type.
        2. Merge actual duplicate rows (same user, same type).
        This runs on module install/upgrade.
        """
        try:
            env = api.Environment(self._cr, SUPERUSER_ID, {})
            Line = env["wing.distribution.line"].with_context(active_test=False)

            # Step 1: Split multi-type rows
            bad_multi = Line.search([]).filtered(lambda l: len(l.distribution_type_ids) > 1 and l.user_id)
            if bad_multi:
                _logger.info("Wing Distribution: splitting %s multi-type line(s).", len(bad_multi))
                for line in bad_multi:
                    tids = line.distribution_type_ids.ids
                    keep_tid = tids[0]
                    # Create new rows for extra types ONLY if they don't already exist for this user.
                    for tid in tids[1:]:
                        existing = Line.search([("user_id", "=", line.user_id.id), ("distribution_type_ids", "in", [tid]), ("id", "!=", line.id)], limit=1)
                        if existing:
                            if not existing.active:
                                existing.with_context(wing_distribution_no_split=True).write({"active": True})
                            continue
                        Line.create({
                            "user_id": line.user_id.id,
                            "distribution_type_ids": [(6, 0, [tid])],
                            "status": line.status or "new",
                            "active": line.active,
                            "round_id": line.round_id.id if line.round_id else False,
                        })
                    line.with_context(wing_distribution_no_split=True).write({"distribution_type_ids": [(6, 0, [keep_tid])]})

            # Step 2: Merge ACTUAL duplicates (same user, same type)
            # Find all (user, type) pairs with > 1 row.
            self.env.cr.execute("""
                SELECT user_id, type_id, count(*)
                FROM wing_distribution_line_type_rel r
                JOIN wing_distribution_line l ON l.id = r.line_id
                GROUP BY user_id, type_id
                HAVING count(*) > 1
            """)
            dupes = self.env.cr.fetchall()
            if dupes:
                _logger.info("Wing Distribution: merging %s duplicate user-type pairs.", len(dupes))
                for user_id, type_id, count in dupes:
                    rows = Line.search([("user_id", "=", user_id), ("distribution_type_ids", "in", [type_id])], order="round_id desc, status desc, id asc")
                    keep = rows[0]
                    to_remove = rows[1:]
                    _logger.info("Wing Distribution: user %s type %s has %s rows. Keeping ID %s, removing %s", user_id, type_id, count, keep.id, to_remove.ids)
                    to_remove.unlink()

        except Exception:
            _logger.exception("Wing Distribution: failed to normalize distribution lines during init().")

    def write(self, vals):
        # Special: distribution_type_ids must always be ONE type per row.
        # If user selects multiple tags on update (or multi_edit), we split them into multiple rows.
        
        # 1. Base case: normal write if no types involved AND no multi-type rows in self
        if "distribution_type_ids" not in vals and not any(len(rec.distribution_type_ids) > 1 for rec in self):
            return super().write(vals)

        # 2. Advanced case: handle splitting/merging
        no_split_ctx = self.env.context.get("wing_distribution_no_split")
        if no_split_ctx:
            return super().write(vals)

        commands = vals.get("distribution_type_ids")
        other_vals = {k: v for k, v in vals.items() if k != "distribution_type_ids"}
        created_or_revived = 0

        for rec in self:
            # Determine target types for this record
            if "distribution_type_ids" in vals:
                desired_ids = self._apply_m2m_commands(rec.distribution_type_ids.ids, commands)
            else:
                desired_ids = rec.distribution_type_ids.ids
            
            desired_ids = [i for i in desired_ids if i]

            # Field is required -> if empty, delete the row
            if not desired_ids:
                if other_vals:
                    super(WingDistributionLine, rec.with_context(wing_distribution_no_split=True)).write(other_vals)
                rec.unlink()
                continue

            # Keep one type on this row
            keep_id = False
            for cid in rec.distribution_type_ids.ids:
                if cid in desired_ids:
                    keep_id = cid
                    break
            if not keep_id:
                keep_id = desired_ids[0]

            # Update this row
            base_write_vals = dict(other_vals)
            base_write_vals["distribution_type_ids"] = [(6, 0, [keep_id])]
            super(WingDistributionLine, rec.with_context(wing_distribution_no_split=True)).write(base_write_vals)

            # Ensure other desired types exist as separate rows
            for tid in desired_ids:
                if tid == keep_id:
                    continue
                existing = self.with_context(active_test=False).search([
                    ("user_id", "=", rec.user_id.id if isinstance(rec.user_id.id, int) else False),
                    ("distribution_type_ids", "in", [tid]),
                ], limit=1)
                
                if existing:
                    revive_vals = {}
                    if not existing.active:
                        revive_vals["active"] = True
                    if "user_id" in other_vals:
                        revive_vals["user_id"] = other_vals["user_id"]
                    # If a round is already running, join it immediately (status=False).
                    # Otherwise mark as "new" to join the next round.
                    if "status" not in vals:
                        active_round_id = self._get_active_round_id_for_type(tid)
                        if active_round_id:
                            revive_vals["status"] = False
                            revive_vals["round_id"] = active_round_id
                        else:
                            revive_vals["status"] = "new"
                    
                    if revive_vals:
                        super(WingDistributionLine, existing.with_context(wing_distribution_no_split=True)).write(revive_vals)
                        created_or_revived += 1
                else:
                    create_vals = {
                        "user_id": rec.user_id.id,
                        "distribution_type_ids": [(6, 0, [tid])],
                        "status": "new",
                        "active": other_vals.get("active", rec.active),
                    }
                    if rec.round_id:
                        create_vals["round_id"] = rec.round_id.id
                    self.create(create_vals)
                    created_or_revived += 1

        # Notify frontend
        if created_or_revived:
            try:
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id,
                    "wing_distribution_multi_created",
                    {"count": created_or_revived},
                )
            except Exception:
                pass
        return True

    def _get_used_user_ids_in_lines(self, distribution_type_id=None, exclude_line_id=None):
        """User IDs already selected in wing distribution lines (so they are removed from selection)."""
        domain = []
        if distribution_type_id:
            domain.append(("distribution_type_ids", "in", [distribution_type_id.id]))
        if exclude_line_id:
            domain.append(("id", "!=", exclude_line_id))
        existing = self.with_context(active_test=False).search(domain)
        return existing.mapped("user_id").ids

    def _get_user_ids_with_all_types(self, exclude_line_id=None):
        """User IDs that already have all 4 types (walk_in, website, 6033, affiliate). Exclude from selection."""
        DistributionType = self.env["wing.distribution.type"]
        DistributionLine = self.env["wing.distribution.line"].with_context(active_test=False)
        types = DistributionType.search([("code", "in", ["walk_in", "website", "6033", "affiliate"])])
        if len(types) < 4:
            return []
        type_ids = set(types.ids)
        domain = []
        if exclude_line_id:
            domain.append(("id", "!=", exclude_line_id))
        lines = DistributionLine.search(domain)
        user_type_map = {}  # user_id -> set of type ids they have
        for line in lines:
            if not line.user_id:
                continue
            uid = line.user_id.id
            if uid not in user_type_map:
                user_type_map[uid] = set()
            user_type_map[uid].update(line.distribution_type_ids.ids)
        return [uid for uid, have in user_type_map.items() if type_ids.issubset(have)]

    @api.depends("user_id", "team_id")
    def _compute_type_ids_already_used_by_user(self):
        """Distribution types this user already has in other lines.
        Always filters by the integer user_id so that two different users who
        happen to share the same display name are never confused with each other.
        """
        for rec in self:
            if not rec.user_id:
                rec.type_ids_already_used_by_user = self.env["wing.distribution.type"]
                continue
            # Use the integer primary key — never a name — to avoid any
            # accidental name-based resolution when two users share the same name.
            uid = rec.user_id.id
            if not isinstance(uid, int):
                rec.type_ids_already_used_by_user = self.env["wing.distribution.type"]
                continue
            rec_id = rec.id if isinstance(rec.id, int) else None
            domain = [("user_id", "=", uid)]
            if rec_id:
                domain.append(("id", "!=", rec_id))
            lines = self.with_context(active_test=False).search(domain)
            rec.type_ids_already_used_by_user = lines.mapped("distribution_type_ids")

    @api.depends("distribution_type_ids", "user_id")
    def _compute_user_domain_ids(self):
        """Eligible users: exclude users who have all 4 types (walk_in, website, 6033, affiliate)."""
        if not self:
            return
        eligible = self[0]._get_walkin_eligible_users()
        for rec in self:
            rec_id = rec.id if isinstance(rec.id, int) else None
            exclude_ids = set(self._get_user_ids_with_all_types(exclude_line_id=rec_id))
            rec.user_domain_ids = eligible.filtered(lambda u: u.id not in exclude_ids)

    @api.onchange("user_id", "distribution_type_ids")
    def _onchange_user_type_for_domain(self):
        """Exclude users who have all 4 types from selection."""
        for rec in self:
            users = rec._get_walkin_eligible_users()
            exclude_id = rec.id if isinstance(rec.id, int) else (rec._origin.id if rec._origin and isinstance(rec._origin.id, int) else None)
            used_ids = set(rec._get_user_ids_with_all_types(exclude_line_id=exclude_id))
            available = users.filtered(lambda u: u.id not in used_ids)
            return {"domain": {"user_id": [("id", "in", available.ids)]}}
        return {}

    def _get_walkin_eligible_users(self):
        """All active sales persons, supervisors, wing managers, and sales managers with a wing. Uses batch wing resolution to avoid N queries."""
        users = self.env["res.users"]
        # Supervisors (name = res.users)
        supervisors = self.env["property.sales.supervisor"].search([])
        users |= supervisors.mapped("name")
        # Salespersons from mapping
        self.env.cr.execute("SELECT DISTINCT user_id FROM property_salesperson_mapping WHERE user_id IS NOT NULL")
        sp_ids = [row[0] for row in self.env.cr.fetchall()]
        if sp_ids:
            users |= self.env["res.users"].browse(sp_ids)
        # Wing managers
        wing_managers = self.env["property.sales.wing"].search([]).mapped("manager_id")
        users |= wing_managers
        # Sales managers (team managers)
        sales_managers = self.env["property.sales.team"].search([]).mapped("manager_id")
        users |= sales_managers
        # Active only
        users = users.filtered(lambda u: u.active and u.id)
        if not users:
            return users
        # Batch: which of these users have a wing (one pass, no per-user queries)
        wing_by_user = self._get_wing_for_user_batch(users)
        return users.filtered(lambda u: wing_by_user.get(u.id))

    def _get_team_for_user(self, user):
        if not user:
            return False
        supervisor = self.env["property.sales.supervisor"].search(
            [("name", "=", user.id)], limit=1
        )
        if supervisor and supervisor.sales_team_id:
            return supervisor.sales_team_id
        if supervisor:
            team = self.env["property.sales.team"].search(
                [("supervisor_ids", "in", supervisor.id)], limit=1
            )
            if team:
                return team

        mapping = self.env["property.salesperson.mapping"].search(
            [("user_id", "=", user.id)], limit=1
        )
        if mapping and mapping.supervisor_id:
            return self.env["property.sales.team"].search(
                [("supervisor_ids", "in", mapping.supervisor_id.id)], limit=1
            )
        return False

    def _get_wing_for_user(self, user):
        if not user:
            return False
        # Wing manager: user is manager of a wing
        wing_as_manager = self.env["property.sales.wing"].search(
            [("manager_id", "=", user.id)], limit=1
        )
        if wing_as_manager:
            return wing_as_manager
        # Sales manager: user is manager of a team, get that team's wing
        team_as_manager = self.env["property.sales.team"].search(
            [("manager_id", "=", user.id)], limit=1
        )
        if team_as_manager:
            wing = self.env["property.sales.wing"].search(
                [("team_ids", "in", team_as_manager.id)], limit=1
            )
            if wing:
                return wing
        # Supervisor / salesperson path
        supervisor = self.env["property.sales.supervisor"].search(
            [("name", "=", user.id)], limit=1
        )
        if supervisor and supervisor.sales_team_id and supervisor.sales_team_id.wing_id:
            return supervisor.sales_team_id.wing_id
        team = self._get_team_for_user(user)
        if team:
            wing = self.env["property.sales.wing"].search(
                [("team_ids", "in", team.id)], limit=1
            )
            return wing
        return False


class WingDistributionTeamState(models.Model):
    _name = "wing.distribution.team.state"
    _description = "Wing Distribution Team State"
    _rec_name = "wing_id"

    wing_id = fields.Many2one("property.sales.wing", string="Wing", required=True)
    distribution_type_id = fields.Many2one(
        "wing.distribution.type", string="Distribution Type", required=True
    )
    supervisor_count = fields.Integer(string="Supervisor Count", default=0)
    weight = fields.Float(string="Weight", digits=(12, 6), default=0.0)
    status = fields.Selection([("served", "Served")], string="Status", default=False)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "team_type_unique",
            "unique(wing_id, distribution_type_id)",
            "Wing state already exists for this distribution type.",
        ),
    ]
