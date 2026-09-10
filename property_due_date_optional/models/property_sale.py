from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    date_optional = fields.Boolean(
        string="Date Optional",
        related='payment_term_id.date_optional',
        store=True,
        readonly=False,
        help="Allows this specific line to bypass due date requirements."
    )

class PropertySale(models.Model):
    _inherit = 'property.sale'

    @api.constrains('payment_schedule_type', 'payment_installment_line_ids')
    def _check_time_based_due_dates(self):
        """ 
        OVERRIDE: intercept the original validation logic to exempt lines 
        where date_optional is True.
        """
        for sale in self:
            if sale.payment_schedule_type == 'time':
                for line in sale.payment_installment_line_ids:
                    
                    if line.date_optional:
                        continue
                        
                    is_paid = getattr(line, 'is_fully_paid', False)
                    if not hasattr(line, 'is_fully_paid'):
                        is_paid = line.expected_amount > 0 and line.paid_amount >= line.expected_amount
                    
                    if not line.due_date and not is_paid:
                        raise ValidationError(_(
                            "Please set a Due Date for all unpaid payment installments when the schedule type is 'Time Based' (unless marked as 'Date Optional')."
                        ))