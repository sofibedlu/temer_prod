from odoo import models, fields, api

class SupportAdditionalTaskWizard(models.TransientModel):
    _name = 'support.additional.task.wizard'
    _description = 'Additional Task Wizard'

    support_id = fields.Many2one('support.management', string='Support Job', required=True)
    location_ids = fields.Many2many('support.location', string='Site / Office Location', required=True)
    department_ids = fields.Many2many('support.department', string='Department', required=True)
    category_ids = fields.Many2many('support.category', string='Category', required=True)
    task_count = fields.Integer(string='Task #', default=1, required=True)
    description = fields.Text(string='Task Description', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.env['support.additional.task'].create({
            'support_id': self.support_id.id,
            'location_ids': [(6, 0, self.location_ids.ids)],
            'department_ids': [(6, 0, self.department_ids.ids)],
            'category_ids': [(6, 0, self.category_ids.ids)],
            'task_count': self.task_count,
            'description': self.description,
        })
        # Post to chatter
        self.support_id.message_post(body=f"Additional Task Performed: {self.description}")
        return {'type': 'ir.actions.act_window_close'}
