from odoo import models, fields

class SupportManagementAchievement(models.Model):
    _name = 'support.management.achievement'
    _description = 'Main Achievement'
    _order = 'sequence, id'

    support_id = fields.Many2one('support.management', string='Job Order', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    text = fields.Char(string='Achievement', required=True)
