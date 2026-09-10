# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BankDocumentType(models.Model):
    _name = 'bank.document.type'
    _rec_name = 'name'
    name = fields.Char(string="Name", required=True)

class PaymentCancellationReason(models.Model):
    _name = 'payment.cancellation.reason'
    name = fields.Char(string="Reason", required=True)


class Banks(models.Model):
    _name = 'bank.configuration'
    _rec_name = 'rec_name'
    _order = 'create_date desc'
    bank = fields.Char(string="bank", required=True)
    account_number = fields.Char(string="Account", required=True)
    rec_name = fields.Char(string="Bank Code",compute='compute_rec_name')

    @api.depends('bank', 'account_number')
    def compute_rec_name(self):
        for rec in self:
            rec.rec_name = rec.bank + " - " + rec.account_number
            
class PropertyReservationConfig(models.Model):
    _name = 'property.reservation.configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Property Reservation Configuration'

    name = fields.Char(string="Name", required=True, tracking=True)
    reservation_type = fields.Selection([
        ('quick', 'Quick'),
        ('regular', 'Regular'),
        ('special', 'Special'),
    ], string='Reservation Type', default='regular', tracking=True)
    
    payment_type = fields.Selection([
        ('percentage', 'Percentage(%)'),
        ('fixed', 'Fixed'),
    ], string='Payment Type', default='percentage', tracking=True)
    
    amount = fields.Float(string='Amount', required=True, help="This amount is % of first payment in payment term", tracking=True)
    duration_in = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Duration In', default='days', tracking=True)
    
    duration = fields.Integer(string='Duration', required=True, tracking=True)
    is_payment_required = fields.Boolean(string='Is Payment Required', required=True, tracking=True)
    one_time_use = fields.Boolean(string='One-Time Use', default=False, tracking=True)
    is_used_use = fields.Boolean(string='Used', default=False, tracking=True)
    used_by_id = fields.Many2one('res.users', string='Used By', tracking=True)
    amount_string = fields.Char(string="", compute="compute_amount_string")

    def compute_amount_string(self):
        for rec in self:
            rec.amount_string="This amount is % of first payment in payment term"

    @api.constrains('amount', 'duration')
    def _validate_amounts(self):
        for rec in self:
            if rec.amount <= 0 and rec.is_payment_required:
                raise ValidationError(_("Amount must be positive and not zero"))
            if rec.duration <= 0:
                raise ValidationError(_("Duration must be positive and not zero"))