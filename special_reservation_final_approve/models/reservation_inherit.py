# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import html2plaintext


class PropertyReservationSpecialAttachments(models.Model):
    _inherit = 'property.reservation'

    # Persistent multiple attachments for special reservation approval
    special_attachment_ids = fields.Many2many(
        'ir.attachment',
        'property_reservation_special_attachment_rel',
        'reservation_id', 'attachment_id',
        string='Special Request Attachments',
    )

    def _fix_special_attachment_access(self):
        """
        Ensure all special_attachment_ids are linked to this reservation via
        res_model/res_id so Odoo's default ir.attachment record rule grants
        read access to any user who can read the reservation.
        """
        for rec in self:
            if not rec.special_attachment_ids:
                continue
            attachments_to_fix = rec.special_attachment_ids.filtered(
                lambda a: a.res_model != 'property.reservation' or a.res_id != rec.id
            )
            if attachments_to_fix:
                attachments_to_fix.sudo().write({
                    'res_model': 'property.reservation',
                    'res_id': rec.id,
                })

    def write(self, vals):
        res = super().write(vals)
        if 'special_attachment_ids' in vals:
            self._fix_special_attachment_access()
        return res

    @api.constrains('is_special_reservation', 'request_letter')
    def _check_request_letter_not_blocking(self):
        """
        Override: if special_attachment_ids exist, auto-populate request_letter
        so the view-level required constraint is satisfied.
        """
        for rec in self:
            if rec.is_special_reservation and not rec.request_letter:
                if rec.special_attachment_ids:
                    rec.sudo().write({
                        'request_letter': rec.special_attachment_ids[0].datas
                    })

    def _notify_by_web_push_prepare_payload(self, message, msg_vals=False):
        """
        Override to inject the special reservation push body from context
        so the phone notification shows the correct body text.
        """
        payload = super()._notify_by_web_push_prepare_payload(message, msg_vals=msg_vals)
        # If a custom push body was set in context, use it
        push_body = self.env.context.get('special_reservation_push_body')
        if push_body:
            payload['options']['body'] = push_body
        return payload
