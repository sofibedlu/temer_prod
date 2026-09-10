# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PropertySpecialDiscount(models.Model):
    _name = 'property.special.discount'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Property Special Discount'

    partner_id = fields.Many2one('res.partner', string="Customer", 
                                tracking=True, required=True)
    property_id = fields.Many2one('property.property',
                                 domain=[('state', 'in', ['available'])],
                                 string="Property", required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', tracking=True)
    attachment = fields.Binary(string="Attachment", required=True)
    discount = fields.Float(string="Discount")
    discount_start_from = fields.Selection(
        [
            ("1", "Fires Payment Term"),
            ("2", "Last Payment Term"),
        ],
        string="Discount Apply From",
        required=True,
        default="1")

    @api.constrains('discount')
    def _check_discount(self):
        for record in self:
            if record.discount <= 0:
                raise ValidationError(_("Discount must be greater than zero"))

    def approve_discount(self):
        self.ensure_one()
        self.status = "approved"

    def reject_discount(self):
        self.ensure_one()
        self.status = "rejected"