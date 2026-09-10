from odoo import models, fields, api, _
from ..models.access_control import require_feature

class MilestoneUpdateWizard(models.TransientModel):
    _name = 'property.milestone.update.wizard'
    _description = 'Batch Milestone Date Update'

    site_id = fields.Many2one('property.site', string='Site / Project', required=True)
    payment_structure_id = fields.Many2one(
        related='site_id.payment_structure_id', 
        string='Technical Payment Structure'
    )
    payment_term_line_id = fields.Many2one(
        'property.payment.term.line', 
        string='Installment (Payment Term Line)', 
        required=True
    )
    new_due_date = fields.Date(string='New Due Date', required=True, default=fields.Date.today)

    def action_confirm(self):
        self.ensure_one()
        require_feature(self.env, "milestone_update", message="You are not allowed to batch update milestone due dates.")

        domain = [
            ('site_id', '=', self.site_id.id),
            ('state', '!=', 'paid'),
            ('collection_id.state', '=', 'active')
        ]
        
        # By ID or Name
        target_line = self.payment_term_line_id
        if target_line.name:
            domain += ['|', ('payment_term_line_id', '=', target_line.id), ('name', '=', target_line.name)]
        else:
            domain += [('payment_term_line_id', '=', target_line.id)]

        installments = self.env['collection.installment'].search(domain)
        
        if not installments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Records Found',
                    'message': 'No unpaid installments found for this payment term line on this site.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        
        # Batch Update
        installments.with_context(due_date_update_source='batch_milestone').write({'due_date': self.new_due_date})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f"Updated due date to {self.new_due_date} for {len(installments)} installments.",
                'type': 'success',
                'sticky': False,
            }
        }