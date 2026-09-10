from odoo import models, fields

class SupportManagementHistory(models.Model):
    _name = 'support.management.history'
    _description = 'Support Management History'
    _order = 'date desc, id desc'

    support_id = fields.Many2one('support.management', string='Task', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Employee', required=True, ondelete='cascade')
    date = fields.Datetime(string='Date Marked Not Completed', default=fields.Datetime.now, required=True)
    description = fields.Text(string='Description', readonly=True)
    category_ids = fields.Many2many(related='support_id.category_ids', string='Category', readonly=True)
    assigned_date = fields.Datetime(related='support_id.assigned_date', string='Assignment Date', readonly=True)

    def action_open_job(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Job Order',
            'view_mode': 'form',
            'res_model': 'support.management',
            'res_id': self.support_id.id,
            'target': 'current',
        }

