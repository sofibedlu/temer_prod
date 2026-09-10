from odoo import models, fields, _
from markupsafe import Markup

class VoidContractWizard(models.TransientModel):
    _name = 'void.contract.wizard'
    _description = 'Void Contract Wizard'

    sale_id = fields.Many2one('property.sale', string='Sale', required=True, readonly=True)
    reason = fields.Text(string='Reason for Voiding', required=True)

    def action_submit_request(self):
        self.ensure_one()
        request = self.env['property.contract.void.request'].create({
            'sale_id': self.sale_id.id,
            'reason': self.reason,
        })
        
        self.sale_id.message_post(
            body=Markup("<b>Void Request Created</b><br/>"
                        "Reference: %s<br/>"
                        "Reason: %s") % (request.name, self.reason),
        )
        return {'type': 'ir.actions.act_window_close'}