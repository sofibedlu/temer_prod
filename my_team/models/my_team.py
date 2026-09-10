from odoo import models, fields, api, _
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class MyTeamMember(models.Model):
    """
    A transient-like read model that represents a flattened view of the
    team hierarchy visible to the currently logged-in Wing Manager or
    Sales Manager.

    Records are computed on-the-fly via a @api.model method and stored
    in a real table so that standard list/form views work without a
    custom controller.  The table is refreshed every time the user opens
    the view (see _auto_refresh action).
    """
    _name = 'my.team.member'
    _description = 'My Team Member'
    _order = 'role_level asc, user_name asc'

    # ── identity ──────────────────────────────────────────────────────────
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    user_name = fields.Char(string='Name', readonly=True)
    user_login = fields.Char(string='Username', readonly=True)
    user_email = fields.Char(string='Email', readonly=True)
    user_phone = fields.Char(string='Phone', readonly=True)
    user_image = fields.Binary(
        string='Photo',
        related='user_id.image_128',
        readonly=True,
    )

    # ── hierarchy ─────────────────────────────────────────────────────────
    role_level = fields.Integer(string='Level', readonly=True,
                                help='1=Wing Manager, 2=Sales Manager, 3=Supervisor, 4=Salesperson')
    role = fields.Selection([
        ('wing_manager',  'Wing Manager'),
        ('sales_manager', 'Sales Manager'),
        ('supervisor',    'Supervisor'),
        ('salesperson',   'Salesperson'),
    ], string='Role', readonly=True)

    wing_id = fields.Many2one('property.sales.wing', string='Wing', readonly=True)
    wing_name = fields.Char(string='Wing', readonly=True)

    team_id = fields.Many2one('property.sales.team', string='Team', readonly=True)
    team_manager_name = fields.Char(string='Sales Manager', readonly=True)

    supervisor_id = fields.Many2one('property.sales.supervisor', string='Supervisor Record', readonly=True)
    supervisor_name = fields.Char(string='Supervisor', readonly=True)

    # owner: the manager who "owns" this view snapshot
    owner_id = fields.Many2one('res.users', string='Owner', readonly=True)

    # ── helpers ───────────────────────────────────────────────────────────

    @api.model
    def _get_my_team_data(self):
        """
        Return a list of dicts describing every person in the hierarchy
        below (and including) the current user, depending on their role.

        Supported roles:
          • Wing Manager  – sees their wing + all teams + all supervisors
                            + all salespersons inside that wing.
          • Sales Manager – sees their team + all supervisors + all
                            salespersons inside that team.

        Raises AccessError if the current user is neither.
        """
        uid = self.env.uid
        rows = []

        # ── Wing Manager branch ───────────────────────────────────────────
        wing = self.env['property.sales.wing'].search(
            [('manager_id', '=', uid)], limit=1
        )
        if wing:
            # Only list people UNDER the wing manager (not themselves)
            for team in wing.team_ids:
                # Sales manager of this team — skip if it's the logged-in user
                if team.manager_id.id != uid:
                    rows.append(self._make_row(
                        user=team.manager_id,
                        role='sales_manager', level=2,
                        wing=wing, team=team,
                    ))

                for sup_rec in team.supervisor_ids:
                    # Skip if supervisor is the logged-in user
                    if sup_rec.name.id != uid:
                        rows.append(self._make_row(
                            user=sup_rec.name,
                            role='supervisor', level=3,
                            wing=wing, team=team, supervisor=sup_rec,
                        ))

                    for mapping in sup_rec.salespersons:
                        # Skip if salesperson is the logged-in user
                        if mapping.user_id.id != uid:
                            rows.append(self._make_row(
                                user=mapping.user_id,
                                role='salesperson', level=4,
                                wing=wing, team=team, supervisor=sup_rec,
                            ))
            return rows

        # ── Sales Manager branch ──────────────────────────────────────────
        team = self.env['property.sales.team'].search(
            [('manager_id', '=', uid)], limit=1
        )
        if team:
            wing = team.wing_id  # computed field

            # Only list people UNDER the sales manager (not themselves)
            for sup_rec in team.supervisor_ids:
                # Skip if supervisor is the logged-in user
                if sup_rec.name.id != uid:
                    rows.append(self._make_row(
                        user=sup_rec.name,
                        role='supervisor', level=3,
                        wing=wing, team=team, supervisor=sup_rec,
                    ))

                for mapping in sup_rec.salespersons:
                    # Skip if salesperson is the logged-in user
                    if mapping.user_id.id != uid:
                        rows.append(self._make_row(
                            user=mapping.user_id,
                            role='salesperson', level=4,
                            wing=wing, team=team, supervisor=sup_rec,
                        ))
            return rows

        # ── Neither ───────────────────────────────────────────────────────
        raise AccessError(_(
            "You are not a Wing Manager or Sales Manager. "
            "You do not have access to the My Team view."
        ))

    @api.model
    def _make_row(self, user, role, level,
                  wing=None, team=None, supervisor=None):
        """Build a single value-dict for create/write."""
        return {
            'user_id':          user.id if user else False,
            'user_name':        user.name if user else '',
            'user_login':       user.login if user else '',
            'user_email':       user.email if user else '',
            'user_phone':       user.partner_id.phone or user.partner_id.mobile or '' if user else '',
            'role':             role,
            'role_level':       level,
            'wing_id':          wing.id if wing else False,
            'wing_name':        wing.name if wing else '',
            'team_id':          team.id if team else False,
            'team_manager_name': team.manager_id.name if team else '',
            'supervisor_id':    supervisor.id if supervisor else False,
            'supervisor_name':  supervisor.name.name if supervisor else '',
            'owner_id':         self.env.uid,
        }

    # ── public action ─────────────────────────────────────────────────────

    def action_ban_user(self):
        """
        Ban the team member:
          1. Remove them from the wing/team/supervisor structure.
          2. Set active = False on their res.users record (disables login).

        Removal logic per role:
          - salesperson  → delete their property.salesperson.mapping row
          - supervisor   → unlink from team's supervisor_ids M2M
          - sales_manager→ unlink team from wing's team_ids M2M
          - wing_manager → not allowed (cannot ban yourself or a wing manager)
        """
        self.ensure_one()

        if not self.user_id:
            return

        if self.role == 'wing_manager':
            raise AccessError(_("You cannot ban a Wing Manager through this interface."))

        # ── 1. Remove from structure ──────────────────────────────────────
        if self.role == 'salesperson':
            # Delete the salesperson mapping record(s) for this user
            mappings = self.env['property.salesperson.mapping'].sudo().search(
                [('user_id', '=', self.user_id.id)]
            )
            mappings.sudo().unlink()

        elif self.role == 'supervisor':
            sup_rec = self.env['property.sales.supervisor'].sudo().search(
                [('name', '=', self.user_id.id)]
            )
            if sup_rec:
                self.env['property.wing.config.supervisor.line'].sudo().search(
                    [('supervisor_id', 'in', sup_rec.ids)]
                ).unlink()

                teams = self.env['property.sales.team'].sudo().search(
                    [('supervisor_ids', 'in', sup_rec.ids)]
                )
                for team in teams:
                    team.sudo().write({'supervisor_ids': [(3, sup_rec.id)]})

                sup_rec.sudo().unlink()

        elif self.role == 'sales_manager':
            team = self.team_id
            if team and team.wing_id:
                team.wing_id.sudo().write({'team_ids': [(3, team.id)]})
            if team:
                team.sudo().unlink()

        # ── 2. Deactivate the user (sets active=False in res.users) ───────
        self.user_id.sudo().write({'active': False})

        # ── 3. Remove this snapshot record and refresh the list ───────────
        owner_uid = self.owner_id.id or self.env.uid
        self.search([('owner_id', '=', owner_uid)]).unlink()

        return {
            'type': 'ir.actions.act_window',
            'name': _('My Team'),
            'res_model': 'my.team.member',
            'view_mode': 'tree,form',
            'domain': [('owner_id', '=', owner_uid)],
            'target': 'current',
        }

    @api.model
    def action_refresh_my_team(self):
        """
        Delete the current user's previous snapshot and rebuild it.
        Called from the menu / button so the view is always fresh.
        """
        uid = self.env.uid
        # Remove stale records for this user
        self.search([('owner_id', '=', uid)]).unlink()

        # Rebuild
        rows = self._get_my_team_data()
        for row in rows:
            self.create(row)

        return {
            'type': 'ir.actions.act_window',
            'name': _('My Team'),
            'res_model': 'my.team.member',
            'view_mode': 'tree,form',
            'domain': [('owner_id', '=', uid)],
            'context': {'search_default_group_role': 1},
            'target': 'current',
        }
