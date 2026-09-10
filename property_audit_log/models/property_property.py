# -*- coding: utf-8 -*-
from odoo import models, api, _

AUDIT_SKIP_FIELDS = frozenset({
    'message_follower_ids', 'message_partner_ids', 'message_ids',
    'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id',
    'activity_date_deadline', 'activity_summary',
    'activity_exception_decoration', 'activity_exception_icon',
    '__last_update', 'write_date', 'write_uid', 'create_date', 'create_uid',
    'display_name',
})


class PropertyPropertyAudit(models.Model):
    _inherit = 'property.property'

    def _audit_fields_from_vals(self, vals):
        """Any field sent on save — no role filter, all users logged the same way."""
        return [
            fname for fname in vals
            if fname not in AUDIT_SKIP_FIELDS and fname in self._fields
            and self._fields[fname].type not in ('one2many', 'many2many', 'binary')
        ]

    def _snapshot_raw_values(self, field_names):
        snapshots = {}
        for rec in self:
            snapshots[rec.id] = {fname: rec[fname] for fname in field_names}
        return snapshots

    def _tracking_commands(self, rec, field_names, before_raw):
        if not field_names:
            return []
        tracked = rec.fields_get(
            field_names, attributes=('string', 'type', 'selection', 'currency_field'),
        )
        commands = []
        for fname in field_names:
            if fname not in tracked or fname not in before_raw.get(rec.id, {}):
                continue
            initial = before_raw[rec.id][fname]
            new_val = rec[fname]
            if new_val == initial or (not new_val and not initial):
                continue
            commands.append([0, 0, self.env['mail.tracking.value']._create_tracking_values(
                initial, new_val, fname, tracked[fname], rec,
            )])
        return commands

    def _log_property_chatter(self, field_names=None, before_raw=None, body=False):
        """Post change on property chatter — author = whoever made the change."""
        self.ensure_one()
        author = self.env.user.partner_id
        if not author:
            return
        tracking_value_ids = []
        if field_names and before_raw:
            tracking_value_ids = self._tracking_commands(self, field_names, before_raw)
        if not tracking_value_ids and not body:
            return
        self.with_context(property_audit_log_skip=True).message_post(
            body=body or '',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
            author_id=author.id,
            tracking_value_ids=tracking_value_ids,
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._log_property_chatter(
                field_names=['state'],
                before_raw={rec.id: {'state': False}},
            )
        return records

    def write(self, vals):
        if self.env.context.get('property_audit_log_skip') or not vals:
            return super().write(vals)

        field_names = self._audit_fields_from_vals(vals)
        before_raw = self._snapshot_raw_values(field_names) if field_names else {}

        res = super().write(vals)

        for rec in self:
            changed = []
            for fname in field_names:
                old_raw = before_raw.get(rec.id, {}).get(fname)
                if rec[fname] == old_raw or (not rec[fname] and not old_raw):
                    continue
                changed.append(fname)
            if changed:
                rec._log_property_chatter(field_names=changed, before_raw=before_raw)
        return res

    def _log_state_button(self, label, before_states):
        for rec in self:
            old_state = before_states.get(rec.id)
            if old_state == rec.state:
                continue
            rec._log_property_chatter(
                field_names=['state'],
                before_raw={rec.id: {'state': old_state}},
            )

    def action_available(self):
        before = {r.id: r.state for r in self}
        super().action_available()
        self._log_state_button(_('Available button'), before)
        return True

    def action_draft(self):
        before = {r.id: r.state for r in self}
        super().action_draft()
        self._log_state_button(_('Draft button'), before)
        return True
