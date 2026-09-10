# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    state = fields.Selection(
        selection_add=[('lock', 'Lock')],
        ondelete={'lock': 'set default'},
    )
    state_before_lock = fields.Selection(
        selection=[('draft', 'Draft'), ('available', 'Available')],
        string="State Before Lock",
        readonly=True,
        copy=False,
    )
    is_locked = fields.Boolean(string="Locked", default=False)
    locked_by_id = fields.Many2one('res.users', string="Locked By", readonly=True)
    locked_date = fields.Datetime(string="Locked Date", readonly=True)
    lock_on_expire = fields.Boolean(
        string="Lock on Expiry",
        default=False,
        help="If set, property will be locked automatically when its reservation expires.",
    )
    lock_on_expire_by_id = fields.Many2one(
        'res.users',
        string="Lock on Expiry Scheduled By",
        readonly=True,
        copy=False,
        help="User who scheduled the lock-on-expiry.",
    )
    lock_on_expire_date = fields.Datetime(
        string="Lock on Expiry Scheduled On",
        readonly=True,
        copy=False,
    )

    @api.depends('is_locked')
    def _compute_lock_display(self):
        for rec in self:
            rec.lock_display = '🔒' if rec.is_locked else ''

    lock_display = fields.Char(compute='_compute_lock_display', string="")

    def action_lock(self):
        if not self.env.user.has_group('property_lock_unlock.property_lock_group'):
            raise UserError(_("You do not have permission to lock properties."))
        for rec in self:
            if rec.state == 'lock':
                raise UserError(_("Property %s is already locked.") % rec.name)
            if rec.state not in ('draft', 'available'):
                raise UserError(_("Only draft or available properties can be locked."))
            now = fields.Datetime.now()
            rec.write({
                'state_before_lock': rec.state,
                'state': 'lock',
                'is_locked': True,
                'locked_by_id': self.env.user.id,
                'locked_date': now,
            })
            rec.message_post(
                body=_("🔒 Property locked by <b>%s</b> on %s") % (
                    self.env.user.name, fields.Datetime.to_string(now),
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_lock_reserved_info(self):
        """Schedule lock on expiry for reserved properties."""
        if not self.env.user.has_group('property_lock_unlock.property_lock_group'):
            raise UserError(_("You do not have permission to lock properties."))
        for rec in self:
            if rec.lock_on_expire:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Already Scheduled"),
                        'message': _("This property is already scheduled to lock when the reservation expires."),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            rec.sudo().write({
                'lock_on_expire': True,
                'lock_on_expire_by_id': self.env.user.id,
                'lock_on_expire_date': fields.Datetime.now(),
            })
            # Also flag the active reservation so the cron uses per-reservation scope
            active_reservation = self.env['property.reservation'].search([
                ('property_id', '=', rec.id),
                ('status', 'in', ['reserved', 'requested']),
            ], limit=1)
            if active_reservation:
                active_reservation.sudo().write({
                    'reservation_lock_on_expire': True,
                    'reservation_lock_on_expire_by_id': self.env.user.id,
                    'reservation_lock_on_expire_date': fields.Datetime.now(),
                })
            rec.message_post(
                body=_("🔒 Lock on expiry scheduled by <b>%s</b>: property will be locked when the reservation expires.") % (
                    self.env.user.name,
                ),
                subtype_xmlid='mail.mt_note',
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Lock Scheduled"),
                'message': _("This property will be locked automatically when the reservation expires."),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_unlock(self):
        if not self.env.user.has_group('property_lock_unlock.property_unlock_group'):
            raise UserError(_("You do not have permission to unlock properties."))
        for rec in self:
            if rec.state != 'lock':
                raise UserError(_("Property %s is not locked.") % rec.name)
            prev_state = rec.state_before_lock or 'draft'
            locked_by_name = rec.locked_by_id.name or _("Unknown")
            now = fields.Datetime.now()
            rec.write({
                'state': prev_state,
                'state_before_lock': False,
                'is_locked': False,
            })
            rec.message_post(
                body=_("🔓 Property unlocked by <b>%s</b> on %s (was locked by <b>%s</b> on %s)") % (
                    self.env.user.name,
                    fields.Datetime.to_string(now),
                    locked_by_name,
                    fields.Datetime.to_string(rec.locked_date) if rec.locked_date else _("unknown date"),
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_available(self):
        if any(rec.is_locked for rec in self):
            raise UserError(_("Cannot mark as Available: the property is locked."))
        return super().action_available()

    def action_draft(self):
        if any(rec.is_locked for rec in self):
            raise UserError(_("Cannot mark as Draft: the property is locked."))
        return super().action_draft()

    def write(self, vals):
        # When a property leaves 'reserved' state, clear lock_on_expire so the
        # next reservation starts clean. History is kept on the reservation record.
        new_state = vals.get('state')
        if new_state and new_state != 'reserved':
            for rec in self:
                if rec.state == 'reserved' and rec.lock_on_expire:
                    vals = dict(vals, lock_on_expire=False)
                    break
        return super().write(vals)
