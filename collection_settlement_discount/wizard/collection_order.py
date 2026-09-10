from odoo import models, fields

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    discount_allocation_ids = fields.One2many(
        'discount.request.allocation',
        'collection_id',
        string="Discount Allocations",
        readonly=True
    )

class DiscountRequestAllocation(models.Model):
    _name = 'discount.request.allocation'
    _description = 'Discount Request Allocation'

    request_id = fields.Many2one('discount.request', string="Request", ondelete='cascade')
    collection_id = fields.Many2one('collection.order', string="Collection Order")
    installment_id = fields.Many2one('collection.installment', string="Applied Installment")
    amount = fields.Monetary(string="Applied Discount Amount", currency_field='currency_id')
    currency_id = fields.Many2one(related='collection_id.currency_id')

class DiscountRequestPreviewLine(models.Model):
    _name = 'discount.request.preview.line'
    _description = 'Discount Allocation Preview'

    request_id = fields.Many2one('discount.request', ondelete='cascade')
    installment_id = fields.Many2one('collection.installment', string='Installment')
    applied_discount = fields.Monetary(string='Applied Discount', currency_field='currency_id')
    remaining_amount = fields.Monetary(string='Remaining After Discount', currency_field='currency_id')
    currency_id = fields.Many2one(related='installment_id.currency_id')