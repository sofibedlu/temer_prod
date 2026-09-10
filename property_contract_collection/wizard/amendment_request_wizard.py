from odoo import models, fields
from markupsafe import Markup

class AmendmentRequestWizard(models.TransientModel):
    _name = 'amendment.request.wizard'
    _description = 'Amendment Request Wizard'

    collection_id = fields.Many2one('collection.order', required=True)
    current_partner_id = fields.Many2one('res.partner', related='collection_id.partner_id', string="Current Customer")
    new_partner_name = fields.Char(string='New Customer (Optional)', help="Enter the name of the new customer if the customer is being changed during this amendment.")
    is_schedule_change = fields.Boolean(string="Involves Schedule Change", default=False, help="Check this if the amendment involves adjusting payment amounts, dates, or merging installments.")
    reason = fields.Text(string='Reason for Amendment', required=True)
    proposed_changes = fields.Html(string='Proposed Schedule Changes', help="Tell the contract team exactly what installments and dates to change.")

    def action_submit_request(self):
        self.ensure_one()
        request = self.env['property.schedule.amendment.request'].sudo().create({
            'collection_id': self.collection_id.id,
            'new_partner_name': self.new_partner_name if self.new_partner_name else False,
            'is_schedule_change': self.is_schedule_change,
            'reason': self.reason,
            'proposed_changes': self.proposed_changes if self.is_schedule_change else False
        })
        message_body = Markup(
            "<b>Amendment Request Submitted</b><br/>"
            "Ref: {}<br/>"
            "Pre-Approved Schedule Change: {}<br/>"
            "Reason: {}"
        ).format(request.name, 'Yes' if self.is_schedule_change else 'No', self.reason)

        self.collection_id.sudo().message_post(body=message_body)
        return {'type': 'ir.actions.act_window_close'}