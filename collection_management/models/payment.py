from odoo import models, fields, api

class PropertyPayment(models.Model):
    _name = 'property.payment'
    _description = 'Payment Transaction'
    _order = 'payment_date desc, id desc'

    installment_id = fields.Many2one('collection.installment', string='Collection Installment', ondelete='cascade')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='installment_id.currency_id')
    payment_date = fields.Date(string='Date', default=fields.Date.today, required=True)
    journal_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check'),
        ('mobile', 'Mobile Money')
    ], string='Method', default='bank')

    collection_installment_id = fields.Many2one(
        'collection.installment', 
        string='Collection Installment', 
        ondelete='cascade'
    )
    reference = fields.Char(string='Reference / Receipt')
    memo = fields.Char(string='Memo')

