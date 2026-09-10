# -*- coding: utf-8 -*-
from odoo import models, fields, api

_APPROVAL_STATES = ('submitted', 'supervisor', 'manager', 'ceo')
_COMMIT_STATES = _APPROVAL_STATES + ('approved',)
_PAYMENT_MANAGER_GROUPS = (
    'special_reservation.group_supervisor',
    'special_reservation.group_manager',
    'special_reservation.group_ceo',
    'ahadubit_property_reservation.finance_team_approval_group',
    'temer_structure.access_property_sales_supervisor_group',
    'temer_structure.access_property_sales_team_manager_group',
    'temer_structure.access_property_wing_manager_group',
)


class SpecialApprovalWizardManagerPayment(models.Model):
    _inherit = 'special.approval.wizard'

    can_manage_payment_lines = fields.Boolean(
        compute='_compute_can_manage_payment_lines',
        store=False,
    )

    def _user_can_manage_special_payments(self):
        return any(self.env.user.has_group(xmlid) for xmlid in _PAYMENT_MANAGER_GROUPS)

    @api.depends('state', 'amount')
    def _compute_can_manage_payment_lines(self):
        can_manage = self._user_can_manage_special_payments()
        for rec in self:
            rec.can_manage_payment_lines = (
                can_manage
                and rec.state in _APPROVAL_STATES
                and (rec.amount or 0.0) > 0.0
            )

    def write(self, vals):
        existing_line_ids = {}
        track_new_lines = 'payment_line_ids' in vals
        if track_new_lines:
            for rec in self:
                existing_line_ids[rec.id] = set(rec.payment_line_ids.ids)

        result = super().write(vals)

        if track_new_lines:
            for rec in self:
                # After submit, every new payment line must be committed immediately
                # so _cleanup_abandoned_payment_lines does not delete it on reopen.
                if rec.state == 'draft':
                    continue
                before = existing_line_ids.get(rec.id, set())
                new_line_ids = set(rec.payment_line_ids.ids) - before
                if not new_line_ids:
                    continue
                new_lines = self.env['property.reservation.payment'].sudo().browse(
                    list(new_line_ids)
                )
                new_lines.write({
                    'is_wizard_temp': False,
                    'is_new_line': False,
                })
                if hasattr(rec, '_create_receipt_records_for_lines'):
                    rec._create_receipt_records_for_lines(new_lines)

        return result

    def _cleanup_abandoned_payment_lines(self):
        """Commit approval-stage payment lines instead of deleting them on reopen."""
        self.ensure_one()
        reservation = self.reservation_id
        if reservation and reservation.state in _COMMIT_STATES:
            temp_lines = self.env['property.reservation.payment'].sudo().search([
                ('reservation_id', '=', reservation.id),
                ('is_wizard_temp', '=', True),
            ])
            if temp_lines:
                temp_lines.write({
                    'is_wizard_temp': False,
                    'is_new_line': False,
                })
                if hasattr(self, '_create_receipt_records_for_lines'):
                    self._create_receipt_records_for_lines(temp_lines)
            return
        return super()._cleanup_abandoned_payment_lines()
