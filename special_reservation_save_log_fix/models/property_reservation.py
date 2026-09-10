# -*- coding: utf-8 -*-
from odoo import fields, models


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    # So Save on Special Approval Form logs amount edits next to duration.
    special_amount = fields.Float(tracking=True)

    def action_view_special_approval(self):
        """Reuse the latest wizard for this reservation so Save updates it.

        Also refresh defaults from the reservation so Duration/Amount/Reason
        always match what was last saved.
        """
        self.ensure_one()
        action = super().action_view_special_approval()
        if not isinstance(action, dict):
            return action

        wizard = self.env['special.approval.wizard'].sudo().search(
            [('reservation_id', '=', self.id)],
            order='id desc',
            limit=1,
        )
        ctx = dict(action.get('context') or {})
        ctx.update({
            'default_reservation_id': self.id,
            'default_reason': self.special_reason or False,
            'default_amount': self.special_amount or 0.0,
            'default_duration': self.special_duration or 0,
            'default_duration_in': getattr(self, 'special_duration_in', None) or 'days',
        })
        action['context'] = ctx

        if wizard:
            # Keep wizard in sync with reservation before opening.
            wiz_vals = {}
            if (wizard.duration or 0) != (self.special_duration or 0):
                wiz_vals['duration'] = self.special_duration or 0
            if 'duration_in' in wizard._fields and 'special_duration_in' in self._fields:
                res_unit = self.special_duration_in or 'days'
                if (wizard.duration_in or 'days') != res_unit:
                    wiz_vals['duration_in'] = res_unit
            if (wizard.amount or 0.0) != (self.special_amount or 0.0):
                wiz_vals['amount'] = self.special_amount or 0.0
            if (wizard.reason or '') != (self.special_reason or ''):
                wiz_vals['reason'] = self.special_reason or wizard.reason
            if wiz_vals:
                # Avoid recursive reservation writes while refreshing wizard display.
                wizard.with_context(skip_special_reservation_sync=True).write(wiz_vals)
            action['res_id'] = wizard.id

        return action
