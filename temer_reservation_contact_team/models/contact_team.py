# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReservationContractTeam(models.Model):
    _name = "reservation.contact.team"
    _description = "Reservation Contract Team"
    _order = "create_date desc"

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'This user is already in the Contract Team.'),
    ]

    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Inactive members are excluded from automatic assignment.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
    )
    status = fields.Selection(
        [
            ("new", "New"),
            ("served", "Served"),
        ],
        string="Status",
        default="new",
    )

    # Plain stored booleans — no compute, only inverse so the group is synced on toggle.
    # Default show_mine=True so every new member gets "Show Mine" automatically.
    show_mine = fields.Boolean(
        string="Show Mine",
        inverse="_inverse_show_mine",
        store=True,
        default=True,
        help="User sees only reservations assigned to themselves in Assigned Sales.",
    )
    show_all = fields.Boolean(
        string="Show All",
        inverse="_inverse_show_all",
        store=True,
        default=False,
        help="User sees all assigned reservations and can use Confirm/Approve buttons.",
    )

    def _inverse_show_mine(self):
        group_mine = self.env.ref(
            'temer_reservation_contact_team.group_assigned_sales_show_mine',
            raise_if_not_found=False,
        )
        group_all = self.env.ref(
            'temer_reservation_contact_team.group_assigned_sales_show_all',
            raise_if_not_found=False,
        )
        for rec in self:
            if not rec.user_id or not group_mine:
                continue
            if rec.show_mine:
                if rec.show_all and group_all:
                    raise ValidationError(
                        "Only one of 'Show Mine' or 'Show All' can be selected at a time."
                    )
                rec.user_id.sudo().write({'groups_id': [(4, group_mine.id)]})
            else:
                rec.user_id.sudo().write({'groups_id': [(3, group_mine.id)]})

    def _inverse_show_all(self):
        group_mine = self.env.ref(
            'temer_reservation_contact_team.group_assigned_sales_show_mine',
            raise_if_not_found=False,
        )
        group_all = self.env.ref(
            'temer_reservation_contact_team.group_assigned_sales_show_all',
            raise_if_not_found=False,
        )
        for rec in self:
            if not rec.user_id or not group_all:
                continue
            if rec.show_all:
                if rec.show_mine and group_mine:
                    raise ValidationError(
                        "Only one of 'Show Mine' or 'Show All' can be selected at a time."
                    )
                rec.user_id.sudo().write({'groups_id': [(4, group_all.id)]})
            else:
                rec.user_id.sudo().write({'groups_id': [(3, group_all.id)]})

    def _remove_groups_from_user(self, user):
        """Remove show_mine/show_all groups from a user (when removed from team)."""
        for xml_id in [
            'temer_reservation_contact_team.group_assigned_sales_show_mine',
            'temer_reservation_contact_team.group_assigned_sales_show_all',
        ]:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group:
                user.sudo().write({'groups_id': [(3, group.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('show_mine', True)
        records = super().create(vals_list)
        # Grant show_mine group immediately for all new records that have it on
        records.filtered('show_mine')._inverse_show_mine()
        return records

    def write(self, vals):
        old_users = {rec.id: rec.user_id for rec in self}
        res = super().write(vals)
        for record in self:
            old_user = old_users.get(record.id)
            if 'user_id' in vals and old_user and old_user != record.user_id:
                other = self.search([('user_id', '=', old_user.id), ('id', '!=', record.id)])
                if not other:
                    self._remove_groups_from_user(old_user)
        return res

    def unlink(self):
        for record in self:
            if record.user_id:
                other = self.search([('user_id', '=', record.user_id.id), ('id', '!=', record.id)])
                if not other:
                    self._remove_groups_from_user(record.user_id)
        return super().unlink()
