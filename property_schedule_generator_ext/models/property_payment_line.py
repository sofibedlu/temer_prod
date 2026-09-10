from odoo import models, fields, api, _

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    due_date = fields.Date(string="Due Date")

    @api.onchange('sale_id', 'expected_amount', 'expected')
    def _onchange_dynamic_due_date_assignment(self):
        """
        Dynamically assign or clear the due date when a user adds a new line
        based on the parent's schedule type.
        """
        for rec in self:
            if rec.sale_id:
                schedule_type = rec.sale_id.payment_schedule_type
                if schedule_type == 'progress':
                    rec.due_date = False

                elif schedule_type == 'time' and not rec.due_date:
                   rec.due_date = fields.Date.context_today(self)