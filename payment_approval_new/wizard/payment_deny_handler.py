# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PaymentDenyHandler(models.TransientModel):
    _name = 'payment.deny.handler'
    _description = 'Deny Payment Handler'

    payment_record_id = fields.Many2one('payment.approval.record', string='Payment Record')
    payment_record_ids = fields.Many2many('payment.approval.record', string='Payment Records')
    reason = fields.Text(string='Reason for Denial', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('default_payment_record_id'):
            res['payment_record_id'] = self._context.get('default_payment_record_id')
        if self._context.get('default_payment_record_ids'):
            res['payment_record_ids'] = [(6, 0, self._context.get('default_payment_record_ids', []))]
        return res

    def action_confirm_deny(self):
        """Confirm denial of payment(s)"""
        self.ensure_one()
        records = self.payment_record_ids if self.payment_record_ids else (self.payment_record_id if self.payment_record_id else self.env['payment.approval.record'])
        if records:
            records.do_deny_confirm(self.reason)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Incoming Payment'),
            'res_model': 'payment.approval.record',
            'view_mode': 'tree',
            'domain': [],
            'context': {'search_default_draft': 1},
            'target': 'current',
        }

