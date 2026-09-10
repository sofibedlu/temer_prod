from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    advance_remaining_total = fields.Monetary(
        string="Advance Remaining Total",
        compute="_compute_advance_remaining_total",
        store=True,
        currency_field='currency_id',
        help="The total unpaid (residual) amount of all installments marked as 'Advance Remaining'."
    )

    @api.depends('installment_ids.is_advance_remaining', 'installment_ids.amount_residual')
    def _compute_advance_remaining_total(self):
        for order in self:
            total = sum(
                line.amount_residual 
                for line in order.installment_ids 
                if line.is_advance_remaining
            )
            order.advance_remaining_total = total