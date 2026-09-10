from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    date_optional = fields.Boolean(
        string="Date Optional",
        related='payment_term_line_id.date_optional',
        store=True,
        readonly=False
    )

    @api.constrains('due_date', 'collection_id')
    def _check_due_date_required_for_time_based(self):
        """
        OVERRIDE: Excludes lines marked as date_optional from the Time-Based constraint.
        """
        if self.env.context.get('collection_creation_bypass'):
            return

        for rec in self:
            if rec.date_optional:
                continue

            is_paid = rec.state == 'paid' or (
                rec.amount_total > 0 and 
                float_compare(rec.amount_paid, rec.amount_total, precision_digits=2) >= 0
            )

            if rec.collection_id and rec.collection_id.payment_schedule_type == 'time':
                if not rec.due_date and not is_paid:
                    raise ValidationError(_(
                        "Due Date is required for all unpaid installments when Payment Schedule Type is Time Based (unless marked as 'Date Optional')."
                    ))