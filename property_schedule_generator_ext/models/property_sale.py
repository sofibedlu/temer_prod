from odoo import models, fields, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    @api.onchange('payment_schedule_type')
    def _onchange_payment_schedule_type_ext(self):
        """set today's date for empty due dates"""
        if self.payment_schedule_type == 'time':
            for line in self.payment_installment_line_ids:
                if not line.due_date:
                    line.due_date = fields.Date.context_today(self)

    def action_open_due_date_generator(self):
        self.ensure_one()
        return {
            'name': 'Generate Due Dates',
            'type': 'ir.actions.act_window',
            'res_model': 'property.due.date.generator.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id}
        }