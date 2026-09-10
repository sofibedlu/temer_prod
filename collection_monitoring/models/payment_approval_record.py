# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PaymentApprovalRecordCollectionMonitoring(models.Model):
    _inherit = 'payment.approval.record'

    # Related fields for filters and group by
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='installment_id.property_id',
        store=True,
        readonly=True,
    )
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        related='installment_id.site_id',
        store=True,
        readonly=True,
    )
    installment_name = fields.Char(
        string='Installment Name',
        related='installment_id.name',
        store=True,
        readonly=True,
    )
    installment_price = fields.Monetary(
        string='Price',
        related='installment_id.amount_total',
        store=True,
        readonly=True,
        currency_field='currency_id',
    )
    display_status = fields.Char(
        string='Status',
        compute='_compute_display_status',
        store=True,
    )

    @api.depends('state')
    def _compute_display_status(self):
        mapping = {
            'draft': 'Pending',
            'approved': 'Paid',
            'denied': 'Denied',
        }
        for rec in self:
            rec.display_status = mapping.get(rec.state, rec.state or '')
