# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ReceiptApprovalRecord(models.Model):
    _inherit = 'receipt.approval.record'

    can_approve_receipt = fields.Boolean(compute='_compute_can_approve_receipt')

    site_company_id = fields.Many2one(
        'site.company',
        string='Site Company',
        compute='_compute_site_company_id',
        store=True,
        readonly=True,
    )

    def _compute_can_approve_receipt(self):
        is_viewer = self.env.user.has_group(
            'receipt_dashboard_viewer.group_receipt_dashboard_viewer',
        )
        for rec in self:
            rec.can_approve_receipt = not is_viewer

    @api.depends('site_id', 'site_id.company_id')
    def _compute_site_company_id(self):
        MappingLine = self.env.get('site.company.mapping.line')
        for rec in self:
            company = rec.site_id.company_id if rec.site_id else False
            if not company and rec.site_id and MappingLine is not None:
                line = MappingLine.sudo().search([('site_id', '=', rec.site_id.id)], limit=1)
                company = line.company_id if line else False
            rec.site_company_id = company
