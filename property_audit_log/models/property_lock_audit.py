# -*- coding: utf-8 -*-
from odoo import models, _


class PropertyPropertyLockAudit(models.Model):
    _inherit = 'property.property'

    def _log_lock_action(self, note, before_state):
        self.ensure_one()
        if before_state != self.state:
            self._log_property_chatter(
                field_names=['state'],
                before_raw={self.id: {'state': before_state}},
            )
        else:
            self._log_property_chatter(body=note)

    def action_lock(self):
        before = {r.id: r.state for r in self}
        res = super().action_lock()
        for rec in self:
            rec._log_lock_action(
                _('Property locked by %s') % self.env.user.name,
                before.get(rec.id),
            )
        return res

    def action_unlock(self):
        before = {r.id: r.state for r in self}
        res = super().action_unlock()
        for rec in self:
            rec._log_lock_action(
                _('Property unlocked by %s') % self.env.user.name,
                before.get(rec.id),
            )
        return res

    def action_lock_reserved_info(self):
        before_expire = {r.id: r.lock_on_expire for r in self}
        res = super().action_lock_reserved_info()
        for rec in self:
            if rec.lock_on_expire and not before_expire.get(rec.id):
                rec._log_property_chatter(
                    body=_('Lock on expiry scheduled by %s') % self.env.user.name,
                )
        return res
