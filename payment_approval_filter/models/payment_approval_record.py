# -*- coding: utf-8 -*-

from odoo import models, fields


class PaymentApprovalRecord(models.Model):
    _inherit = 'payment.approval.record'

    site_id = fields.Many2one('property.site', related='installment_id.site_id', store=True, string='Site', readonly=True)
    site_name = fields.Char(related='site_id.name', store=True, string='Site Name', readonly=True)

