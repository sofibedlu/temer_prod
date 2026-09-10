# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PropertyStateChangeConfirmWizard(models.TransientModel):
    _name = 'property.state.change.confirm.wizard'
    _description = 'Confirm Property State Change'

    property_ids = fields.Many2many(
        'property.property',
        string='Properties',
        required=True,
    )
    target_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('available', 'Available'),
        ],
        string='Target State',
        required=True,
    )
    message = fields.Text(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        target_state = res.get('target_state') or self.env.context.get('default_target_state')
        if 'message' in fields_list:
            if target_state == 'available':
                res['message'] = _(
                    'Are you sure you want to cancel the reservation and set the property available?'
                )
            else:
                res['message'] = _(
                    'Are you sure you want to cancel the reservation and set the property draft?'
                )
        return res

    def action_confirm(self):
        self.ensure_one()
        properties = self.property_ids.with_context(confirm_property_state_change=True)
        if self.target_state == 'available':
            properties.action_available()
        else:
            properties.action_draft()
        return {'type': 'ir.actions.act_window_close'}
