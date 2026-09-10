from odoo import models, fields

class EarlySettlementHistory(models.Model):
    _name = 'early.settlement.history'
    _description = 'Early Settlement Installment History'

    request_id = fields.Many2one('early.settlement.request', string="Request", ondelete='cascade')
    collection_id = fields.Many2one('collection.order', related='request_id.collection_id', store=True)
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')
    
    name = fields.Char(string='Description')
    due_date = fields.Date(string='Due Date')
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id')
    amount_paid = fields.Monetary(string='Paid Amount', currency_field='currency_id')
    amount_residual = fields.Monetary(string='Remaining Amount', currency_field='currency_id')
    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue')
    ], string='Status')