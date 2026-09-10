from odoo import models, fields, api

class ScheduleAmendmentWizard(models.TransientModel):
    _name = 'schedule.amendment.wizard'
    _description = 'Schedule Amendment Wizard'

    sale_id = fields.Many2one('property.sale', required=True, readonly=True)
    reason = fields.Text(string='Reason for Amendment', required=True)

    def action_unlock(self):
        self.ensure_one()
        sale = self.sale_id
        
        # Create History Snapshot
        history = self.env['property.payment.schedule.history'].create({
            'sale_id': sale.id,
            'reason': self.reason,
        })
        
        # Copy current lines to history
        for line in sale.payment_installment_line_ids:
            self.env['property.payment.schedule.history.line'].create({
                'history_id': history.id,
                'name': line.payment_term_id.name if line.payment_term_id else 'Installment',
                'expected_amount': line.expected_amount,
                'paid_amount': line.paid_amount,
                'expected': line.expected,
            })
            
        # Unlock the schedule
        sale.is_schedule_unlocked = True
        sale.message_post(body=f"<b>Payment Schedule Unlocked for Amendment</b><br/>Reason: {self.reason}")
        return {'type': 'ir.actions.act_window_close'}


class PaymentScheduleHistory(models.Model):
    _name = 'property.payment.schedule.history'
    _description = 'Payment Schedule History'
    _order = 'date desc'

    sale_id = fields.Many2one('property.sale', string='Sale', required=True, ondelete='cascade')
    date = fields.Datetime(string='Amendment Date', default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one('res.users', string='Amended By', default=lambda self: self.env.user, readonly=True)
    reason = fields.Text(string='Reason for Amendment', readonly=True)
    line_ids = fields.One2many('property.payment.schedule.history.line', 'history_id', string='Previous Schedule')

class PaymentScheduleHistoryLine(models.Model):
    _name = 'property.payment.schedule.history.line'
    _description = 'Payment Schedule History Line'

    history_id = fields.Many2one('property.payment.schedule.history', required=True, ondelete='cascade')
    name = fields.Char(string='Installment Name')
    expected_amount = fields.Float(string='Expected Amount')
    paid_amount = fields.Float(string='Paid Amount')
    expected = fields.Float(string='Expected(%)')