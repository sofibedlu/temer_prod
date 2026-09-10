from odoo import models, fields, api

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    pending_approval_amount = fields.Monetary(
        string='Pending Amount',
        compute='_compute_pending_approval_amount',
        currency_field='currency_id'
    )

    def _compute_pending_approval_amount(self):
        for rec in self:
            approvals = self.env['payment.approval.record'].search([
                ('installment_id', '=', rec.id),
                ('state', '=', 'draft')
            ])
            rec.pending_approval_amount = sum(approvals.mapped('amount'))