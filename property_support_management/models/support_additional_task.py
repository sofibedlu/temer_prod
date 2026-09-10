from odoo import models, fields

class SupportAdditionalTask(models.Model):
    _name = 'support.additional.task'
    _description = 'Additional Task'
    _order = 'id asc'

    support_id = fields.Many2one('support.management', string='Job Order', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Done By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    location_ids = fields.Many2many('support.location', string='Site / Office Location', required=True)
    department_ids = fields.Many2many('support.department', string='Department', required=True)
    category_ids = fields.Many2many('support.category', string='Category', required=True)
    task_count = fields.Integer(string='Task #', default=1, required=True)
    description = fields.Text(string='Task Description', required=True)
    is_confirmed = fields.Boolean(string="Confirmed", default=False)
