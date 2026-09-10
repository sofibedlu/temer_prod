from odoo import models, api, _
from odoo.exceptions import UserError

class PropertySale(models.Model):
    _inherit = 'property.sale'

    
    def action_render_amharic_names(self):
        self.ensure_one()
        
        # if getattr(self, 'payment_schedule_type', False) != 'time':
        #     raise UserError(_("This action is only available for Time-Based schedules."))

        config = self.env['property.ethiopian.calendar.config'].search([], limit=1)
        if not config:
            config = self.env['property.ethiopian.calendar.config'].create({})

        parent_term_id = self.property_payment_term.id if self.property_payment_term else False

        for line in self.payment_installment_line_ids:
            
            if not line.due_date:
                continue
                
            is_paid = line.state == 'paid' or (line.expected_amount > 0 and line.paid_amount >= line.expected_amount)
            if is_paid:
                continue

            amharic_name = config.convert_date_to_amharic(line.due_date)
            term_line = self.env['property.payment.term.line'].search([('name', '=', amharic_name)], limit=1)
            
            if not term_line:
                term_line = self.env['property.payment.term.line'].create({
                    'name': amharic_name,
                    #'payment_term_id': parent_term_id
                })

            line.payment_term_id = term_line.id

        return True