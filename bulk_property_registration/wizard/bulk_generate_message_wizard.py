# -*- coding: utf-8 -*-
from odoo import fields, models, _


class BulkGenerateMessageWizard(models.TransientModel):
    _name = 'bulk.generate.message.wizard'
    _description = 'Bulk Generate Success Message'

    message = fields.Html(string='Message', readonly=True)
    bulk_id = fields.Many2one('property.bulk.registration', string='Bulk Registration', readonly=True)

    def action_close(self):
        """Close wizard and reload the bulk registration form."""
        self.ensure_one()
        if self.bulk_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'property.bulk.registration',
                'res_id': self.bulk_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
