import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import Markup

_logger = logging.getLogger(__name__)

class CollectionSendSMSWizard(models.TransientModel):
    _name = 'collection.send.sms.wizard'
    _description = 'Send Collection SMS'

    collection_id = fields.Many2one('collection.order', string='Collection', required=True)
    
    installment_id = fields.Many2one(
        'collection.installment', 
        string='Installment', 
        required=True, 
        domain="[('collection_id', '=', collection_id)]"
    )
    
    mobile_no = fields.Char(string='Mobile Number', required=True)
    
    template_selection = fields.Selection([
        ('reminder', 'Payment Reminder'),
        ('overdue', 'Overdue Warning'),
        ('received', 'Payment Received'),
    ], string="Use Template")

    message = fields.Text(string='Message Content', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'collection.order' and active_id:
            collection = self.env['collection.order'].browse(active_id)
            res['collection_id'] = collection.id
            res['mobile_no'] = collection.partner_id.mobile or collection.partner_id.phone or ''
            
        return res

    @api.onchange('template_selection', 'installment_id')
    def _onchange_template(self):
        """Pre-fill message based on template selection"""
        if not self.template_selection or not self.installment_id:
            return

        amount = self.installment_id.amount_residual
        date = self.installment_id.due_date
        ref = self.installment_id.name

        if self.template_selection == 'reminder':
            self.message = f"Dear Customer, a gentle reminder for installment {ref} of {amount} due on {date}. Please pay to avoid penalties. Temer RE."
        elif self.template_selection == 'overdue':
            self.message = f"URGENT: Your installment {ref} is OVERDUE. Please settle {amount} immediately to avoid further action. Temer RE."
        elif self.template_selection == 'received':
            self.message = f"Thank you! We have received payment for installment {ref}. Your account is updated. Temer RE."

    def _send_sms_api(self, mobile, message):
        """
        Send SMS via AfroMessage API
        """
        try:
            # Clean number
            mobile = mobile.replace(' ', '').replace('-', '').replace('+', '')     
            # Credentials
            token = 'eyJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiNlRaUTByWlZLejNoMVg4V3hVWUpUemRmUURTUGVNMFEiLCJleHAiOjE5MTYzMDcyODQsImlhdCI6MTc1ODU0MDg4NCwianRpIjoiNDAzMjQyYzItNjlkOS00MzBjLWI4ZGMtMzM0NDUzNjM5ZGExIn0.AXAEroQlKaAe7orHe2x6vkoZ-kTSfso_-XT_dIqlVbo'
            sender = 'Temer RE'
            from_identifier = 'e80ad9d8-adf3-463f-80f4-7c4b39f7f164'
            
            session = requests.Session()
            base_url = 'https://api.afromessage.com/api/send'
            headers = {'Authorization': 'Bearer ' + token}
            
            # Construct URL
            url = f"{base_url}?from={from_identifier}&sender={sender}&to={mobile}&message={message}"
            # Send Request
            result = session.get(url, headers=headers)
            if result.status_code == 200:
                json_response = result.json()
                if json_response.get('acknowledge') == 'success':
                    return True, "Success"
                else:
                    return False, f"API Error: {json_response}"
            else:
                return False, f"HTTP Error: {result.status_code}"
                
        except Exception as e:
            return False, str(e)

    def action_send_sms(self):
        self.ensure_one()
        
        # Send SMS via API
        success, api_response = self._send_sms_api(self.mobile_no, self.message)
        if not success:
            raise UserError(_("Failed to send SMS: %s") % api_response)

        self.collection_id.sudo().message_post(
            body=Markup(f"<b>SMS Sent regarding {self.installment_id.name}</b><br/>To: {self.mobile_no}<br/>Content: {self.message}"),
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SMS Sent',
                'message': 'The SMS has been sent successfully.',
                'type': 'success',
                'sticky': False,
            }
        }