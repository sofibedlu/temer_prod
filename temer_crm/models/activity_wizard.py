# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TemerLeadActivityWizard(models.TransientModel):
    _name = 'temer.lead.activity.wizard'
    _description = 'Temer Lead Activity Wizard'

    lead_id = fields.Many2one('temer.lead', string='Lead', required=True)
    activity_type = fields.Selection([
        ('call', 'Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('office_visit', 'Office Visit'),
        ('site_visit', 'Site Visit')
    ], string='Activity Type', required=True)

    description = fields.Text(string='Description', required=True)

    @api.model
    def default_get(self, fields):
        res = super(TemerLeadActivityWizard, self).default_get(fields)
        if self._context.get('active_id'):
            res['lead_id'] = self._context['active_id']
        return res

    def action_log_activity(self):
        """Log the activity and update state if needed"""
        self.ensure_one()

        # Create follow-up record
        self.env['temer.lead.followup'].create({
            'lead_id': self.lead_id.id,
            'activity_type': self.activity_type,
            'description': self.description,
        })

        # Update state to follow_up if currently in prospect
        if self.lead_id.state == 'prospect':
            self.lead_id.write({'state': 'follow_up'})

        return {'type': 'ir.actions.act_window_close'}