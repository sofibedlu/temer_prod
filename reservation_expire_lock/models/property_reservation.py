# -*- coding: utf-8 -*-
##############################################################################
#    Reservation Expire Lock
#    Copyright (C) 2024-TODAY Ahadubit Technologies
##############################################################################

from datetime import datetime

from odoo import models, fields, _


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    reservation_lock_on_expire = fields.Boolean(
        string="Lock on Expiry (this reservation)",
        default=False,
        copy=False,
        help="Set when a user schedules lock-on-expiry for this specific reservation. "
             "The cron uses this flag so a new reservation on the same property is not affected.",
    )
    reservation_lock_on_expire_by_id = fields.Many2one(
        'res.users',
        string="Lock on Expiry Scheduled By",
        readonly=True,
        copy=False,
    )
    reservation_lock_on_expire_date = fields.Datetime(
        string="Lock on Expiry Scheduled On",
        readonly=True,
        copy=False,
    )

    def check_expired_reservation(self):
        """
        Override to lock properties on expiry when lock_on_expire is scheduled.
        For reservations with lock_on_expire=True, intercept before base runs and lock instead.
        For everything else, let the base handle it normally.
        """
        now = fields.Datetime.now()
        # Only handle reservations that have lock_on_expire scheduled
        lock_reservations = self.search([
            ('status', '=', 'reserved'),
            ('expire_date', '<=', now),
            ('reservation_lock_on_expire', '=', True),
        ])
        for reservation in lock_reservations:
            prop = reservation.property_id
            reservation.sudo().write({
                'status': 'expired',
                'canceled_time': datetime.now(),
            })
            scheduled_by = reservation.reservation_lock_on_expire_by_id
            state_before = prop.state if prop.state not in ('lock',) else 'available'
            prop.sudo().write({
                'state_before_lock': state_before if state_before in ('draft', 'available') else 'available',
                'state': 'lock',
                'is_locked': True,
                'locked_by_id': scheduled_by.id if scheduled_by else False,
                'locked_date': now,
            })
            prop.sudo().message_post(
                body=_("🔒 Property automatically locked: reservation expired on %s (reservation: %s, lock scheduled by: %s)") % (
                    fields.Datetime.to_string(now),
                    reservation.id,
                    scheduled_by.name if scheduled_by else _("System"),
                ),
                subtype_xmlid='mail.mt_note',
            )
            stage = self.env['crm.stage'].search(
                [('name', 'ilike', 'Follow Up')], limit=1
            )
            if stage and reservation.crm_lead_id:
                reservation.crm_lead_id.write({'stage_id': stage.id})

        # Let the base handle everything else (sets property to available on normal expiry)
        return super().check_expired_reservation()
