from odoo import models, fields

class PartialSettlementSession(models.Model):
    _name = 'partial.settlement.session'
    _description = 'Partial Settlement Session'
    
    name = fields.Char(string='Settlement Reference', required=True)
    collection_id = fields.Many2one('collection.order', string='Collection Order', ondelete='cascade')
    settlement_date = fields.Datetime(string='Settlement Date', default=fields.Datetime.now)
    history_line_ids = fields.One2many('collection.installment.history', 'session_id', string='Installments Merged')
    new_installment_amount = fields.Monetary(string='New Installment Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')

class CollectionInstallmentHistory(models.Model):
    _name = 'collection.installment.history'
    _description = 'Collection Installment History'
    
    session_id = fields.Many2one('partial.settlement.session', string='Settlement Session', ondelete='cascade')
    collection_id = fields.Many2one('collection.order', related='session_id.collection_id', store=True)
    name = fields.Char(string='Description')
    due_date = fields.Date(string='Due Date')
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id')
    amount_paid = fields.Monetary(string='Paid Amount', currency_field='currency_id')
    amount_residual = fields.Monetary(string='Remaining Amount', currency_field='currency_id')
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id')
    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue')
    ], string='Status')
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    linked_installment_id = fields.Many2one('collection.installment', string="Linked Installment")

    def write(self, vals):
        res = super(CollectionInstallment, self).write(vals)
        
        # If the due_date of this installment is updated, update all folded installments linked to it
        if 'due_date' in vals and not self.env.context.get('skip_linked_installment_due_date_update'):
            for record in self:

                linked_installments = self.env['collection.installment'].sudo().search([
                    ('linked_installment_id', '=', record.id),
                    ('due_date', '!=', vals['due_date'])
                ])
                if linked_installments:
                    linked_installments.with_context(skip_linked_installment_due_date_update=True).write({
                        'due_date': vals['due_date']
                    })
        return res