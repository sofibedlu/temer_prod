from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bill_approved_by_id = fields.Many2one(
        'res.users', 
        compute='_compute_bill_approved_by', 
        string="Approved By (From Bill)",
        store=False
    )

    @api.depends('reconciled_bill_ids')
    def _compute_bill_approved_by(self):
        for pay in self:
            if pay.reconciled_bill_ids:
                pay.bill_approved_by_id = pay.reconciled_bill_ids[0].approved_by_id
            else:
                pay.bill_approved_by_id = False