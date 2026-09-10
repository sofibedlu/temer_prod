# -*- coding: utf-8 -*-

from odoo import models


class SpecialApprovalWizardManagerSupervisorSkip(models.Model):
    _inherit = 'special.approval.wizard'

    def _apply_supervisor_skip_state(self):
        """Sales/wing managers skip Submitted and land on Supervisor Approval."""
        for wizard in self:
            reservation = wizard.reservation_id
            if reservation and reservation._should_skip_supervisor_step():
                wizard.write({'state_new': 'supervisor'})
                reservation.write({'state': 'supervisor'})

    def action_submit(self):
        res = super().action_submit()
        self._apply_supervisor_skip_state()
        return res

    def _finalize_and_submit(self):
        """special_reservation_payment Save/Submit uses this, not action_submit."""
        res = super()._finalize_and_submit()
        self._apply_supervisor_skip_state()
        return res
