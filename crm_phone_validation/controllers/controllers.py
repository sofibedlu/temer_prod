from odoo import http
from odoo.http import request
import json

class PhoneValidationController(http.Controller):

    @http.route('/crm_lead/check_phones', type='json', auth='user')
    def check_phone_numbers(self, phone_no=False, phone_ids=False, lead_id=False):
        """
        JSON endpoint for checking phone number duplicates
        """
        if not phone_no and not phone_ids:
            return {'exists': False}

        Lead = request.env['crm.lead']
        result = Lead.check_duplicate_phones(phone_no, phone_ids, lead_id)
        return result