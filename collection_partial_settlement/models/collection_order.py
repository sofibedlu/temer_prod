from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    partial_settlement_session_ids = fields.One2many(
        'partial.settlement.session', 
        'collection_id', 
        string='Partial Settlement Sessions', 
        readonly=True
    )
    has_partial_settlement = fields.Boolean(compute='_compute_has_partial_settlement')

    @api.depends('partial_settlement_session_ids')
    def _compute_has_partial_settlement(self):
        for rec in self:
            rec.has_partial_settlement = bool(rec.partial_settlement_session_ids)

    def action_open_partial_settlement_wizard(self):
        self.ensure_one()
        return {
            'name': 'Partial Settlement',
            'type': 'ir.actions.act_window',
            'res_model': 'partial.settlement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_id': self.id,
            }
        }