# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PropertyReservationExtendInherit(models.Model):
    """
    Extends property.reservation.extend.history to add a two-step approval:
      pending → pending_final_approval → approved
                                       ↘ rejected
    When the normal approver clicks Approve, the extension goes to
    'pending_final_approval' instead of directly to 'approved'.
    The Extension Final Approver (CEO role) then does the final approval.
    """
    _inherit = 'property.reservation.extend.history'

    status = fields.Selection(
        selection_add=[
            ('pending_final_approval', 'Pending Final Approval'),
        ],
    )

    def approve_extension(self):
        """
        Override: instead of directly approving, move to pending_final_approval.
        The reservation extension_status is set to 'pending_final_approval' so
        the reservation form reflects the intermediate state.
        """
        for rec in self:
            if rec.status != 'pending':
                raise ValidationError(_("Only pending extensions can be sent for final approval."))
            rec.reservation_id.sudo().write({'extension_status': 'pending_final_approval'})
            rec.status = 'pending_final_approval'
            # Log a note on the reservation chatter
            try:
                rec.reservation_id.sudo().message_post(
                    body=_("Extension request sent for final approval."),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                _logger.warning("Could not post chatter message: %s", e)

    def action_final_approve_extension(self):
        """
        Final approval by the Extension Final Approver.
        Updates the reservation expire_date and sets statuses to approved.
        """
        for rec in self:
            if rec.status != 'pending_final_approval':
                raise ValidationError(_("Only extensions pending final approval can be finally approved."))
            rec.reservation_id.sudo().write({
                'expire_date': rec.extension_date,
                'extension_status': 'approved',
            })
            rec.status = 'approved'
            try:
                rec.reservation_id.sudo().message_post(
                    body=_("Extension request finally approved. New end date: %s") % rec.extension_date,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                _logger.warning("Could not post chatter message: %s", e)

    def action_final_reject_extension(self):
        """
        Final rejection by the Extension Final Approver.
        """
        for rec in self:
            if rec.status != 'pending_final_approval':
                raise ValidationError(_("Only extensions pending final approval can be rejected here."))
            rec.reservation_id.sudo().write({'extension_status': 'rejected'})
            rec.status = 'rejected'
            try:
                rec.reservation_id.sudo().message_post(
                    body=_("Extension request rejected by final approver."),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                _logger.warning("Could not post chatter message: %s", e)
