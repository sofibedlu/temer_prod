from pprint import pprint

from odoo.http import Controller, request, route
import json
from odoo import http
import re
from odoo.http import request
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.tools.mail import is_html_empty


class CrmController(Controller):
    @route('/api/myPipeline', type='http', auth='none', csrf=False, methods=['GET'])
    def get_my_activity(self, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            if not session_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: No session found"}),
                    headers={'Content-Type': 'application/json'}
                )
            request.session.rotate = False
            user_id = request.session.uid
            if not user_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: Invalid session"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Get the user record
            user = request.env['res.users'].sudo().browse(user_id)

            if not user.exists():
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: User not found"}),
                    headers={'Content-Type': 'application/json'}
                )

            leads = request.env['crm.lead'].sudo().search([('user_id', '=', user_id)])

            # Prepare property data for response
            data = []
            for prop in leads:
                data.append({
                    "id": prop.id,
                    "name": prop.name,
                    "customer": prop.customer_name,
                    "reservation_count": prop.reservation_count,
                    "site_ids": [{"id": site.id, "name": site.name} for site in prop.site_ids],
                    "source":  {"id": prop.source_id.id, "name": prop.source_id.name} if prop.source_id else None,
                    "phones": [{"id": phone.id, "country_id": phone.country_id.id, "phone": phone.phone} for phone in
                              prop.phone_ids],
                    "stage": {"id": prop.stage_id.id, "name": prop.stage_id.name} if prop.stage_id else None,
                })
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )


    @route('/api/createPipeline',  type='http', auth='user', csrf=False, methods=['POST'])
    def create_pipeline(self, **kwargs):
        """API to create a new CRM lead"""

        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            phones=data.get('phones')
            count=0
            lead=False
            for phone in phones:
                country=request.env['res.country'].sudo().search([('id', '=', phone.get('country_id'))])
                if country:
                    ph=phone.get('phone_no')
                    phone_num=f"+{country.phone_code}{ph}"
                    check_phone=request.env['crm.phone'].sudo().search([('phone', '=', phone_num)])
                    if check_phone:
                        return self._error_response(400, "phone number must be uniq")
                    phone_regex = r'^\+?\d{1,15}$'
                    if ph:
                        if not re.match(phone_regex, ph):
                            return self._error_response(400,
                                                        "Invalid phone number format! Please enter a valid phone number.")
                        if country.phone_code == 251:
                            if ph[0] == "0":
                                self._error_response(400,
                                                     "Invalid phone number format! Phone number must not start with 0.")
                            if len(ph) != 9:
                                return self._error_response(400,
                                                            "Invalid phone number format! Please enter a valid phone number.")
                        elif len(phone_num) < 5 or len(phone_num) > 14:
                            return self._error_response(400,
                                                            "Invalid phone number format! Please enter a valid phone number.")

                    if count==0 :
                        site_ids = [(6, 0, data.get('site_ids', []))]
                        lead = request.env['crm.lead'].sudo().create({
                            'customer_name': data.get('customer_name'),
                            'user_id': request.env.user.id,
                            'source_id': data.get('source_id'),
                            'phone_no': phone.get('phone_no'),
                            'country_id':phone.get('country_id'),
                            'site_ids': site_ids
                        })
                        count+=1
                    elif count>0 and lead:
                        lead.write({
                            'phone_no': phone.get('phone_no'),
                            'country_id': phone.get('country_id'),
                        })
                else:
                    return self._error_response(400, "please select valid country")


            return self._success_response({"id": lead.id, "message": "Lead created successfully"})

        except Exception as e:
            return self._error_response(500, str(e))

    @route('/api/updatePipeline', type='http', auth='user', csrf=False, methods=['PUT'])
    def update_pipeline(self, **kwargs):
        """API to update an existing CRM lead"""

        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            lead_id = data.get('id')

            # Ensure 'id' is provided
            if not lead_id:
                return self._error_response(400, "Missing required field: 'id'")

            # Fetch the lead
            lead = request.env['crm.lead'].sudo().browse(lead_id)

            if not lead.exists():
                return self._error_response(404, "Lead not found")

            # Prepare update values
            phones = data.get('phones')
            phone_ids = [phone['id'] for phone in phones if 'id' in phone]
            lead_phone_ids=[]
            if lead.phone_ids:
                lead_phone_ids=lead.phone_ids.ids
            not_in_phone_ids = [id_ for id_ in lead_phone_ids if id_ not in phone_ids]
            if len(not_in_phone_ids):
                request.env['crm.phone'].sudo().search([('id', 'in', not_in_phone_ids)]).unlink()
            new_ids=[]
            for phone in phones:
                phone_id=phone.get('id')
                ph = phone.get('phone')
                country = request.env['res.country'].sudo().search([('id', '=', phone.get('country_id'))])
                _phone = f"+{country.phone_code}{ph}"
                check_phone=request.env['crm.phone'].sudo().search([('phone', '=', _phone)])
                if check_phone and lead.partner_id.id != check_phone.partner_id.id:
                    return self._error_response(400,
                                                "This number is Already Registered, Phone number must be unique!")

                if phone.get('id'):
                    old_phone = request.env['crm.phone'].sudo().browse(phone_id)
                    if old_phone:
                        old_phone.write({
                            'phone': phone.get('phone'),
                            'country_id': phone.get('country_id'),
                        })
                        new_ids.append(old_phone.id)
                else:
                    phone_regex = r'^\+?\d{1,15}$'
                    if ph:
                        if not re.match(phone_regex, ph):
                            return self._error_response(400,
                                                        "Invalid phone number format! Please enter a valid phone number.")
                        if country.phone_code == 251:
                            if ph[0] == "0":
                               return self._error_response(400,
                                                     "Invalid phone number format! Phone number must not start with 0.")
                            if len(str(ph)) != 9:
                                return self._error_response(400,
                                                            "Invalid phone number format! Please enter a valid phone number.")
                        elif len(str(ph)) < 5 or len(str(ph)) > 14:
                            return self._error_response(400,
                                                        "Invalid phone number format! Please enter a valid phone number.")

                    new_phone=request.env['crm.phone'].sudo().create({
                        'partner_id': lead.partner_id.id,
                        'country_id': phone.get('country_id'),
                        'phone': _phone
                    })
                    new_ids.append(new_phone.id)

            update_values = {
                'customer_name': data.get('customer_name', lead.customer_name),
                'source_id': data.get('source_id', lead.source_id.id),
                'site_ids': [(6, 0, data.get('site_ids', lead.site_ids.ids))] if 'site_ids' in data else lead.site_ids,
                'phone_ids': new_ids
            }
            lead.write(update_values)

            return self._success_response({"id": lead.id, "message": "Lead updated successfully"})

        except Exception as e:
            return self._error_response(500, str(e))

    @route('/api/myPipelineDetail', type='http', auth='none', csrf=False, methods=['GET'])
    def get_my_activity_detail(self, id=None, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            if not session_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: No session found"}),
                    headers={'Content-Type': 'application/json'}
                )
            request.session.rotate = False
            user_id = request.session.uid
            if not user_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: Invalid session"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Get the user record
            user = request.env['res.users'].sudo().browse(user_id)

            if not user.exists():
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: User not found"}),
                    headers={'Content-Type': 'application/json'}
                )
            if id:
                lead = request.env['crm.lead'].sudo().search([('id', '=', int(id)), ('user_id', '=', user_id)])
                if lead:
                    data = {
                        "id": lead.id,
                        "name": lead.name,
                        "customer": lead.customer_name,
                        "source_id": lead.source_id.id if lead.source_id else None,
                        "partner_id": lead.partner_id.id if lead.partner_id else None,
                        "user_id": lead.user_id.name if lead.user_id else None,
                        "site_ids": [{"id": site.id, "name": site.name} for site in lead.site_ids],
                        "phone": [{"id": phone.id,"country_id": phone.country_id.id, "phone": phone.phone} for phone in lead.phone_ids],
                        "stage": {"id": lead.stage_id.id, "name": lead.stage_id.name} if lead.stage_id else None,
                        "reservation_count": lead.reservation_count,
                    }
                    return request.make_response(
                        json.dumps({"status": 200, "data": data}),
                        headers={'Content-Type': 'application/json'}
                    )
                else:
                    return request.make_response(
                        json.dumps({"status": 404, "error": "Activity with the given id not found"}),
                        headers={'Content-Type': 'application/json'})

            else:
                return request.make_response(
                    json.dumps({"status": 500, "error": "Pleas request by id"}),
                    headers={'Content-Type': 'application/json'}
                )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/lostReasons', type='http', auth='user', csrf=False, methods=['GET'])
    def lost_reasons(self, **kwargs):

        try:
            session_id = request.httprequest.cookies.get('session_id')
            if not session_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: No session found"}),
                    headers={'Content-Type': 'application/json'}
                )
            request.session.rotate = False
            user_id = request.session.uid
            if not user_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: Invalid session"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Get the user record
            user = request.env['res.users'].sudo().browse(user_id)

            if not user.exists():
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: User not found"}),
                    headers={'Content-Type': 'application/json'}
                )
            reasons = request.env['crm.lost.reason'].sudo().search([])
            data = []
            for prop in reasons:
                data.append({
                    "id": prop.id,
                    "bank": prop.name
                })
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/markAsLost', type='http', auth='user', csrf=False, methods=['POST'])
    def mark_as_lost(self, **kwargs):

        try:
            session_id = request.httprequest.cookies.get('session_id')
            if not session_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: No session found"}),
                    headers={'Content-Type': 'application/json'}
                )
            request.session.rotate = False
            user_id = request.session.uid
            if not user_id:
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: Invalid session"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Get the user record
            user = request.env['res.users'].sudo().browse(user_id)

            if not user.exists():
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: User not found"}),
                    headers={'Content-Type': 'application/json'}
                )
            data = json.loads(request.httprequest.data.decode('utf-8'))
            lost_reason_id = data.get('lost_reason_id')
            lost_feedback = data.get('lost_feedback')
            lead_id = data.get('lead_id')
            crm_lead = request.env['crm.lead'].search([('id', '=', int(lead_id))], limit=1)
            lead_stage = request.env['crm.stage'].search([('is_lost_stage', '=', True)], limit=1)

            if  crm_lead:
                if lead_stage:
                    crm_lead.write({
                         'stage_id':lead_stage.id,
                    })
                if not is_html_empty(lost_feedback):
                    crm_lead._track_set_log_message(
                        Markup('<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>') % (
                            _('Lost Comment'),
                            lost_feedback
                        )
                    )
                res = crm_lead.action_set_lost(lost_reason_id=lost_reason_id)
                if lead_stage:
                    crm_lead.write({
                         'active' : True
                    })
            else:
                return request.make_response(
                    json.dumps({"status": 401, "error": "invalid lead id"}),
                    headers={'Content-Type': 'application/json'}
                )
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )


    def _success_response(self, data):
        """Helper method to format success responses"""
        return request.make_response(
            json.dumps({"status": 200, "data": data}),
            headers={'Content-Type': 'application/json'}
        )

    def _error_response(self, status, message):
        """Helper method to format error responses"""
        return request.make_response(
            json.dumps({"status": status, "error": message}),
            headers={'Content-Type': 'application/json'}
        )

