# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ReceiptDenialReasonType(models.Model):
    _name = 'receipt.denial.reason.type'
    _description = 'Receipt Denial Reason Type'
    _order = 'name'
    
    name = fields.Char(string='Reason Type', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    description = fields.Text(string='Description')
    
    denial_reason_ids = fields.One2many('receipt.denial.reason', 'reason_type_id', string='Denial Reasons')
    denial_count = fields.Integer(string='Usage Count', compute='_compute_denial_count', store=False)
    
    @api.depends('denial_reason_ids')
    def _compute_denial_count(self):
        for rec in self:
            rec.denial_count = len(rec.denial_reason_ids)

