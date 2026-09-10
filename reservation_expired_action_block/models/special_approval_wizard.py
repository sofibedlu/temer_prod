# -*- coding: utf-8 -*-
from odoo import models


class SpecialApprovalWizardExpiredBlock(models.Model):
    _inherit = 'special.approval.wizard'

    def _check_reservation_active_for_approve(self):
        if self.reservation_id:
            self.reservation_id._check_reservation_active_for_approve()

    def action_submit(self):
        self._check_reservation_active_for_approve()
        return super().action_submit()

    def action_supervisor_approve(self):
        self._check_reservation_active_for_approve()
        return super().action_supervisor_approve()

    def action_manager_approve(self):
        self._check_reservation_active_for_approve()
        return super().action_manager_approve()

    def action_final_approve(self):
        self._check_reservation_active_for_approve()
        return super().action_final_approve()
