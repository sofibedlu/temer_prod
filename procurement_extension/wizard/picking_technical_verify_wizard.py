from odoo import models, fields
from markupsafe import Markup

class PickingTechnicalVerifyWizard(models.TransientModel):
    _name = 'picking.technical.verify.wizard'
    _description = 'Technical Verification Wizard'

    picking_id = fields.Many2one('stock.picking', string='Receipt', required=True, readonly=True)
    
    notes = fields.Html(
        string='Inspection Notes', 
        required=True, 
        sanitize=True,
        help="Specify which products passed, which failed, and any conditions."
    )

    def action_confirm(self):
        self.ensure_one()
        picking = self.picking_id.sudo()
        
        picking.write({
            'technical_approved': True,
            'technical_approved_by': self.env.user.id,
            'technical_approval_date': fields.Datetime.now(),
        })
        

        msg = Markup("<b>Technical Inspection Completed</b><br/><b>Notes:</b><br/>{}").format(self.notes or '')
        picking.message_post(body=msg)
        
        return {'type': 'ir.actions.act_window_close'}