# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ReceiptDenialReason(models.Model):
    _name = 'receipt.denial.reason'
    _description = 'Receipt Denial Reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    receipt_record_id = fields.Many2one('receipt.approval.record', string='Receipt Record', required=True, ondelete='cascade', tracking=True)
    reason_type_id = fields.Many2one('receipt.denial.reason.type', string='Reason Type', required=True, tracking=True)
    description = fields.Text(string='Description', required=True, tracking=True)
    
    # Related fields for reporting
    customer_id = fields.Many2one('res.partner', string='Customer', related='receipt_record_id.customer_id', store=True, readonly=True)
    property_id = fields.Many2one('property.property', string='Property', related='receipt_record_id.property_id', store=True, readonly=True)
    site_id = fields.Many2one('property.site', string='Site', related='receipt_record_id.site_id', store=True, readonly=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', related='receipt_record_id.amount', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='receipt_record_id.currency_id', store=True, readonly=True)
    denied_date = fields.Datetime(string='Denied Date', related='receipt_record_id.denied_date', store=True, readonly=True)
    denied_by = fields.Many2one('res.users', string='Denied By', related='receipt_record_id.denied_by', store=True, readonly=True)

