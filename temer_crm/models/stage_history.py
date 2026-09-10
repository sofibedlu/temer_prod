from odoo import models, fields, api
from datetime import datetime


class CrmStageHistory(models.Model):
    _name = 'crm.stage.history'
    _description = 'CRM Stage History'
    _order = 'create_date desc'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    from_stage_id = fields.Many2one('crm.stage', string='From Stage')
    to_stage_id = fields.Many2one('crm.stage', string='To Stage')
    transition_date = fields.Datetime(string='Transition Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
