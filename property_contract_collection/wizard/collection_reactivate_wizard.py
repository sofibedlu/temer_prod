from odoo import models, fields, api, _
from markupsafe import Markup

class CollectionReactivateWizard(models.TransientModel):
    _name = 'collection.reactivate.wizard'
    _description = 'Collection Reactivate Wizard'

    collection_id = fields.Many2one('collection.order', string="Collection Order", required=True)
    reason = fields.Text(string="Reason for Reactivation", required=True)

    def action_confirm_reactivate(self):
        self.ensure_one()
        if self.collection_id.state == 'terminated':
            self.collection_id.write({'state': 'active'})
            self.collection_id.message_post(
                body=Markup("<b>Collection Order Reactivated</b><br/>"
                            "Reason: %s") % self.reason
            )
        return {'type': 'ir.actions.act_window_close'}