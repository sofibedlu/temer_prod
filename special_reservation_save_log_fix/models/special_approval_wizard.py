# -*- coding: utf-8 -*-
from odoo import api, models


class SpecialApprovalWizardSaveLogFix(models.Model):
    _inherit = 'special.approval.wizard'

    # Sync anytime Save can update editable values. View Special Form often
    # opens a fresh wizard, so Duration/Amount/Reason must land on the
    # reservation to survive reopen and show in the log.
    _SYNC_TO_RESERVATION_STATES = (
        'draft',
        'submitted',
        'supervisor',
        'manager',
        'ceo',
    )
    _WIZARD_RESERVATION_SYNC = {
        'duration': 'special_duration',
        'duration_in': 'special_duration_in',
        'amount': 'special_amount',
        'reason': 'special_reason',
    }

    def _sync_editable_fields_to_reservation(self):
        """Always push current editable wizard values onto the reservation."""
        if self.env.context.get('skip_special_reservation_sync'):
            return
        for rec in self:
            reservation = rec.reservation_id
            if not reservation:
                continue
            if reservation.state not in self._SYNC_TO_RESERVATION_STATES:
                continue

            rvals = {}
            for wizard_field, reservation_field in self._WIZARD_RESERVATION_SYNC.items():
                if reservation_field not in reservation._fields:
                    continue
                new_value = getattr(rec, wizard_field)
                old_value = reservation[reservation_field]
                if wizard_field in ('duration', 'amount'):
                    new_value = new_value or 0
                    old_value = old_value or 0
                if new_value != old_value:
                    rvals[reservation_field] = new_value

            if rvals:
                reservation.with_context(
                    tracking_disable=False,
                    mail_notrack=False,
                ).write(rvals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_editable_fields_to_reservation()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_editable_fields_to_reservation()
        return res

    def web_save(self, vals, specification, next_id=None):
        """After every Save (create or write), force reservation update."""
        existing_ids = self.ids
        res = super().web_save(vals, specification, next_id=next_id)

        if existing_ids:
            self.browse(existing_ids)._sync_editable_fields_to_reservation()
            return res

        # First Save on a new form uses create — pick ids from web_read result.
        record_ids = []
        if isinstance(res, list):
            record_ids = [row['id'] for row in res if isinstance(row, dict) and row.get('id')]
        elif isinstance(res, dict) and res.get('id'):
            record_ids = [res['id']]
        if record_ids:
            self.browse(record_ids)._sync_editable_fields_to_reservation()
        return res

    def _retrack_final_approval(self, reservation, old_state, old_expire, old_duration,
                                old_duration_in):
        """Re-apply final approval changes without leaking Approved → CEO."""
        if reservation.state != 'approved':
            return

        final_expire = reservation.expire_date
        final_duration = reservation.special_duration or 0
        final_duration_in = (
            getattr(reservation, 'special_duration_in', None) or 'days'
        )
        old_duration = old_duration or 0
        old_duration_in = old_duration_in or 'days'

        expire_changed = not self._datetime_equal(final_expire, old_expire)
        duration_changed = final_duration != old_duration
        duration_in_changed = (
            'special_duration_in' in reservation._fields
            and final_duration_in != old_duration_in
        )
        need_state_log = old_state and old_state != 'approved'

        if not (expire_changed or duration_changed or duration_in_changed or need_state_log):
            return

        silent_ctx = {
            'tracking_disable': True,
            'mail_notrack': True,
            'mail_create_nosubscribe': True,
            'tracking_disable_message': True,
        }

        revert_vals = {}
        if need_state_log:
            revert_vals['state'] = (
                'ceo' if old_state in ('ceo', 'manager') else old_state
            )
        if expire_changed:
            revert_vals['expire_date'] = old_expire
        if duration_changed:
            revert_vals['special_duration'] = old_duration
        if duration_in_changed:
            revert_vals['special_duration_in'] = old_duration_in

        if revert_vals:
            # Bypass mail.thread.write so Approved → CEO never hits chatter.
            models.Model.write(reservation.with_context(**silent_ctx), revert_vals)
            reservation.invalidate_recordset(
                ['state', 'expire_date', 'special_duration']
                + (['special_duration_in'] if duration_in_changed else [])
            )

        track_vals = {}
        if need_state_log:
            track_vals['state'] = 'approved'
        if expire_changed:
            track_vals['expire_date'] = final_expire
        if duration_changed:
            track_vals['special_duration'] = final_duration
        if duration_in_changed:
            track_vals['special_duration_in'] = final_duration_in

        track_ctx = (
            self._tracking_write_context()
            if hasattr(self, '_tracking_write_context')
            else dict(self.env.context, tracking_disable=False, mail_notrack=False)
        )
        reservation.with_context(**track_ctx).write(track_vals)
        if hasattr(self, '_flush_tracking'):
            self._flush_tracking()
        else:
            self.env.flush_all()
            self.env.cr.precommit.run()
