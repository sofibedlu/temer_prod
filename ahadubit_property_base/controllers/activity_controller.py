from odoo.http import Controller, request, route
import json
from odoo import http
from odoo.http import request
from bs4 import BeautifulSoup
import re
from datetime import timedelta



class ActivityController(Controller):


    @route('/api/activityTypes', type='http', auth='user', csrf=False, methods=['GET'])
    def get_activity_types(self, **kwargs):
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
            activity = request.env['mail.activity.type'].sudo().search([])
            data = []
            for prop in activity:
                data.append({
                    "id": prop.id,
                    "name": prop.name,

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

    @route('/api/activityByPipline', type='http', auth='user', csrf=False, methods=['GET'])
    def get_activity_by_pipline(self, pipline_id=None, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            print(",,,kkkkkkkkkkkkkkkkkkkkkkkkkk: ",session_id)
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
            lead = request.env['crm.lead'].sudo().search([('id','=',pipline_id)])
            data = []
            for prop in lead.message_ids:
                summery = ""
                original_note = ""
                field_id = ""
                new_value_char = ""
                old_value_char = ""
                summary_text = BeautifulSoup(prop.body, "html.parser").get_text(separator=" ", strip=True)

                if prop.mail_activity_type_id:
                    part1_match = re.search(r':(.*?)Original note:', summary_text)
                    summery = part1_match.group(1).strip() if part1_match else ''

                    # Extract part from 'Original note:' to end
                    part2_match = re.search(r'Original note:\s*(.*)', summary_text)
                    original_note = part2_match.group(1).strip() if part2_match else ''

                elif not summary_text:
                    massage=request.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', prop.id)])
                    if massage:
                        field_id = massage.field_id.field_description
                        new_value_char = massage.new_value_char
                        old_value_char = massage.old_value_char
                else:
                    summery=summary_text
                create_date = prop.create_date + timedelta(hours=3)

                data.append({
                    "id": prop.id,
                    "user": prop.create_uid.name,
                    "activity_type": {"id": prop.mail_activity_type_id.id, "name": prop.mail_activity_type_id.name} if prop.mail_activity_type_id else None,
                    "summary": summery,
                    "note": original_note,
                    "field": field_id,
                    "new_value_char": new_value_char,
                    "old_value_char": old_value_char,
                    "create_date":  create_date.strftime('%Y-%m-%d %H:%M:%S') if prop.create_date else None,
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

    @route('/api/createActivity', type='http', auth='user', csrf=False, methods=['POST'])
    def create_activity(self, **kwargs):
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
            create_data=request.env['mail.activity.schedule'].sudo().create({
                'res_model': "crm.lead",
                "res_ids":data.get('res_ids'),
                'activity_type_id': data.get('activity_type_id'),
                'summary': data.get('summary'),
                'note': data.get('note'),

            })
            create_data.write({
                "res_ids": data.get('res_ids')
            })
            create_data.action_schedule_activities_done()
            return request.make_response(
                json.dumps({"status": 200, "message": "Activity created successfully"}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

