from odoo import models, fields, _
from markupsafe import Markup

class PropertyPaymentExtensionWizard(models.TransientModel):
    _inherit = 'property.payment.extension.wizard'

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    def action_confirm_extension(self):
        """Override to create an extension request instead of directly updating the installment."""
        self.ensure_one()
        request = self.env['collection.payment.extension.request'].sudo().create({
            'collection_id': self.collection_id.id,
            'installment_id': self.installment_id.id,
            'current_date': self.current_date,
            'new_date': self.new_date,
            'reason': self.reason,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'state': 'pending'
        })
        
        for att in self.attachment_ids:
            att.write({'res_model': 'collection.payment.extension.request', 'res_id': request.id})
        
        message = Markup("<b>Payment Extension Request Submitted</b> for <b>%s</b><br/>Old Date: %s<br/>Requested Date: %s<br/>Reason: %s") % (
            self.installment_id.name, self.current_date, self.new_date, self.reason
        )
        if self.collection_id:
            self.collection_id.sudo().message_post(body=message)
            
        return {'type': 'ir.actions.act_window_close'}