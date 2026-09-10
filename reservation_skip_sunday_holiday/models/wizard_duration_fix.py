# -*- coding: utf-8 -*-
"""Route duration_fix step to final_approve (not legacy amount=1 handler)."""
from odoo import models

try:
    from odoo.addons.special_reservation_duration_fix.models.wizard_inherit import (
        SpecialApprovalWizardDurationFix,
    )
except ImportError:
    SpecialApprovalWizardDurationFix = None

try:
    from odoo.addons.special_reservation_final_approve.models.special_approval_wizard import (
        SpecialApprovalWizard as SpecialApprovalWizardFinalApprove,
    )
except ImportError:
    SpecialApprovalWizardFinalApprove = None


class SpecialApprovalWizardDurationFixPassthrough(models.Model):
    _inherit = 'special.approval.wizard'

    def action_final_approve(self):
        if hasattr(self, '_check_reservation_not_expired'):
            self._check_reservation_not_expired()
        if SpecialApprovalWizardFinalApprove is not None:
            return SpecialApprovalWizardFinalApprove.action_final_approve(self)
        if SpecialApprovalWizardDurationFix is not None:
            return super(
                SpecialApprovalWizardDurationFix, self
            ).action_final_approve()
        return super().action_final_approve()
