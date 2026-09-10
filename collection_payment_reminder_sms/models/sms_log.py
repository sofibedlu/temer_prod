from odoo import models, fields

class CollectionSmsLog(models.Model):
    _name = 'collection.sms.log'
    _description = 'Collection SMS Log'
    _order = 'create_date desc'

    installment_id = fields.Many2one('collection.installment', string="Installment", required=True, ondelete='cascade')
    collection_id = fields.Many2one('collection.order', related='installment_id.collection_id', string="Collection Order", store=True)
    partner_id = fields.Many2one('res.partner', related='installment_id.partner_id', string="Customer", store=True)
    phone = fields.Char(related='partner_id.mobile', string="Mobile Number")
    
    due_date = fields.Date(related='installment_id.due_date', string="Due Date")
    amount = fields.Monetary(related='installment_id.amount_residual', string="Outstanding Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='installment_id.currency_id')
    sender_id = fields.Many2one('res.users', string="Sender", default=lambda self: self.env.user)
    payment_schedule_type = fields.Selection(related='installment_id.collection_id.payment_schedule_type', string="Schedule Type", store=True)

    message_body = fields.Text(string="Sent Message")
    error_message = fields.Char(string="API Response / Error")

    message_stage = fields.Selection([
        ('first', 'First Reminder'),
        ('second', 'Second Reminder'),
        ('third', 'Third Reminder'),
        ('thank_you', 'Thank You')
    ], string="Message Stage", readonly=True)
    
    status = fields.Selection([
        ('not_sent', 'Message Not Sent'),
        ('sent', 'Message Sent'),
        ('failed', 'Failed')
    ], string="Status", default='not_sent')