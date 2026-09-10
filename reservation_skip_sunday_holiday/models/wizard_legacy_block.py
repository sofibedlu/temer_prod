# -*- coding: utf-8 -*-
"""
Block legacy special_reservation final approve that forces amount=1 and
is_payment_required=True even for zero-amount approvals.
"""
from odoo import models

try:
    from odoo.addons.special_reservation_final_approve.models.special_approval_wizard import (
        SpecialApprovalWizard as SpecialApprovalWizardFinalApprove,
    )
except ImportError:
    SpecialApprovalWizardFinalApprove = None


class SpecialApprovalWizardLegacyBlock(models.Model):
    _inherit = 'special.approval.wizard'

    def action_final_approve(self):
        if SpecialApprovalWizardFinalApprove is not None:
            return SpecialApprovalWizardFinalApprove.action_final_approve(self)
        return super().action_final_approve()
