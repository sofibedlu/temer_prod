# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReceiptDenyWizard(models.TransientModel):
    _name = 'receipt.deny.wizard'
    _description = 'Receipt Deny Wizard'
    
    receipt_record_id = fields.Many2one('receipt.approval.record', string='Receipt Record')
    receipt_record_ids = fields.Many2many('receipt.approval.record', string='Receipt Records')
    reason_type_id = fields.Many2one('receipt.denial.reason.type', string='Reason Type', required=True, domain=[('active', '=', True)])
    description = fields.Text(string='Description', required=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('default_receipt_record_id'):
            res['receipt_record_id'] = self._context.get('default_receipt_record_id')
        if self._context.get('default_receipt_record_ids'):
            res['receipt_record_ids'] = [(6, 0, self._context.get('default_receipt_record_ids', []))]
        return res
    
    def action_confirm_deny(self):
        """Confirm denial of receipt(s)"""
        self.ensure_one()
        
        if not self.reason_type_id:
            raise UserError(_('Please select a reason type.'))
        
        if not self.description:
            raise UserError(_('Please provide a description.'))
        
        # Get records to deny
        records = self.receipt_record_ids if self.receipt_record_ids else (self.receipt_record_id if self.receipt_record_id else self.env['receipt.approval.record'])
        
        if records:
            records.do_deny_confirm(
                reason_type_id=self.reason_type_id.id,
                description=self.description
            )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt Dashboard'),
            'res_model': 'receipt.approval.record',
            'view_mode': 'tree,form',
            'domain': [],
            'context': {'search_default_draft': 1},
            'target': 'current',
        }

