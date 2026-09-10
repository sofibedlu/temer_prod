from odoo import models, fields, api
from odoo.tools import Markup
from ..models.access_control import require_feature

class PropertyPaymentExtensionWizard(models.TransientModel):
    _name = 'property.payment.extension.wizard'
    _description = 'Payment Extension Wizard'

    collection_id = fields.Many2one('collection.order', string='Collection', required=True)
    installment_id = fields.Many2one(
        'collection.installment',
        string='Select Installment',
        required=True,
        domain="[('collection_id','=',collection_id), ('state','!=','paid')]"
    )
    current_date = fields.Date(string='Current Due Date')
    new_date = fields.Date(string='New Extended Date', required=True)
    reason = fields.Text(string='Reason for Extension', required=True)

    @api.onchange('installment_id')
    def _onchange_installment_id(self):
        for rec in self:
            if rec.installment_id:
                rec.current_date = rec.installment_id.extended_date or rec.installment_id.due_date

    def action_confirm_extension(self):
        self.ensure_one()
        require_feature(self.env, "due_date_edit", message="You are not allowed to extend due dates.")
        old_date = self.installment_id.extended_date or self.installment_id.due_date
        # update installment
        self.installment_id.sudo().write({
            'extended_date': self.new_date,
            'due_date': self.new_date,
            'remark': (self.installment_id.remark or '') + "\n[Extension] %s -> %s : %s" % (old_date, self.new_date, self.reason)
        })
        message = Markup("Payment Extension granted for <b>%s</b><br/>Old Date: %s<br/>New Date: %s<br/>Reason: %s") % (
            self.installment_id.name, old_date, self.new_date, self.reason
        )
        if self.collection_id:
            self.collection_id.sudo().message_post(body=message)
        else:
            self.installment_id.collection_id.sudo().message_post(body=message)
        if hasattr(self.installment_id, '_compute_state'):
            self.installment_id.sudo()._compute_state()
        return {'type': 'ir.actions.act_window_close'}