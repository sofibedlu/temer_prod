from odoo.http import Controller, request, route
import json
from odoo import http
import re
from odoo.http import request
import base64

from odoo import models, fields, api,_


class ReservationController(Controller):
    @route('/api/myReservation', type='http', auth='user', csrf=False, methods=['GET'])
    def get_my_reservation(self, **kwargs):
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

            reservations = request.env['property.reservation'].sudo().search([('create_uid','=',user_id)])

            data = []
            for res in reservations:
                data.append({
                    "id": res.id,
                    "property": {"id": res.property_id.id, "name": res.property_id.name} if res.property_id else None,
                    "site": {"id": res.site_id.id, "name": res.site_id.name} if res.site_id else None,
                    "customer": {"id": res.partner_id.id, "name": res.partner_id.name},
                    "reservation_type": {"id": res.reservation_type_id.id,
                                         "name": res.reservation_type_id.name} if res.reservation_type_id else None,
                    "expire_date": res.expire_date.strftime('%Y-%m-%d %H:%M:%S') if res.expire_date else None,
                    "status": res.status,
                    "is_sufficient": res.is_sufficient,
                    "payment_diff": res.payment_diff,
                    # "request_letter": base64.b64encode(res.request_letter).decode() if res.request_letter else None,
                    "expected_amount": res.expected_amount,
                    "extension_status": res.extension_status,
                    "transfer_status": res.transfer_status,
                    "payment_lines": [
                        {"id": payment.id,
                         "amount": payment.amount,
                         # "payment_receipt": base64.b64encode(payment.payment_receipt).decode() if payment.payment_receipt else None,
                         "document_type_id": {"id": payment.document_type_id.id,
                                              "name":payment.document_type_id.name} if payment.document_type_id else None,
                         "bank_id": {"id": payment.bank_id.id,
                                              "name": payment.bank_id.bank} if payment.bank_id else None,

                         "status": payment.payment_status}
                        for payment in res.payment_line_ids
                    ],
                    "extensions":[
                        {
                         "id": ext.id,
                         "property_id":res.property_id.id,
                         "old_end_date": ext.old_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                         "extension_date": ext.extension_date.strftime('%Y-%m-%d %H:%M:%S'),
                         "date": ext.create_date.strftime('%Y-%m-%d %H:%M:%S')
                         }
                        for ext in res.extension_ids
                    ],
                    "transfers": [
                        {
                            "id": transfer.id,
                            "date": transfer.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "old_property": {"id": transfer.old_property_id.id,
                                             "name": transfer.old_property_id.name} if transfer.old_property_id else None,
                            "new_property": {"id": transfer.property_id.id,
                                             "name": transfer.property_id.name} if transfer.property_id else None,
                            "status": transfer.status,
                            "total_paid": transfer.total_paid,
                            "payment_lines": [
                                {"id": payment.id,
                                 "amount": payment.amount} for payment in transfer.payment_line_ids
                            ]} for transfer in res.transfer_ids
                    ]})
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/ReservationDetail', type='http', auth='user', csrf=False, methods=['GET'])
    def get_reservation_detail(self,id=None, **kwargs):
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

            res = request.env['property.reservation'].sudo().search([('id', '=', int(id))])
            if not res:
                return request.make_response(
                    json.dumps({"status": 500, "error": "Reservation With the given id doesn't exist"}),
                    headers={'Content-Type': 'application/json'}
                )
            else:
                data={
                    "id": res.id,
                    "property": {"id": res.property_id.id, "name": res.property_id.name} if res.property_id else None,
                    "site": {"id": res.site_id.id, "name": res.site_id.name} if res.site_id else None,
                    "salesperson_ids": res.salesperson_ids.id if res.salesperson_ids else None,
                    "customer": {"id": res.partner_id.id, "name": res.partner_id.name},
                    "reservation_type": {"id": res.reservation_type_id.id,
                                         "name": res.reservation_type_id.name} if res.reservation_type_id else None,
                    "expire_date": res.expire_date.strftime('%Y-%m-%d %H:%M:%S') if res.expire_date else None,
                    "status": res.status,
                    "is_sufficient": res.is_sufficient,
                    "payment_diff": res.payment_diff,
                    "expected_amount": res.expected_amount,
                    "extension_status": res.extension_status,
                    "transfer_status": res.transfer_status,
                    "request_letter": base64.b64encode(res.request_letter).decode() if res.request_letter else None,
                    "payment_lines": [
                        {
                        "id": payment.id,
                        "ref_number": payment.ref_number,
                        "bank_id": {"id": payment.bank_id.id,
                                    "bank": payment.bank_id.bank} if payment.bank_id else None,
                        "document_type_id": {"id": payment.document_type_id.id,
                                             "bank": payment.document_type_id.name} if payment.document_type_id else None,
                         "amount": payment.amount,
                         "transaction_date": payment.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if payment.transaction_date else None,
                         "payment_receipt": base64.b64encode(payment.payment_receipt).decode() if payment.payment_receipt else None,
                         "status": payment.payment_status
                         }
                        for payment in res.payment_line_ids
                    ],
                    "extensions": [
                        {
                            "id": ext.id,
                            "property_id": res.property_id.id,
                            "old_end_date": ext.old_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "extension_date": ext.extension_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "request_letter": base64.b64encode(
                                ext.request_letter_file).decode() if ext.request_letter_file else None,
                            "date": ext.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "status": ext.status
                        }
                        for ext in res.extension_ids
                    ],
                    "transfers": [
                        {
                            "id": transfer.id,
                            "date": transfer.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "old_property": {"id": transfer.old_property_id.id,
                                             "name": transfer.old_property_id.name} if transfer.old_property_id else None,
                            "new_property": {"id": transfer.property_id.id,
                                             "name": transfer.property_id.name} if transfer.property_id else None,
                            "status": transfer.status,
                            "request_letter": base64.b64encode(
                                transfer.request_letter).decode() if transfer.request_letter else None,
                            "total_paid": transfer.total_paid,
                            "payment_lines": [
                                {"id": payment.id,
                                 "ref_number": payment.ref_number,
                                 "bank_id": {"id": payment.bank_id.id,
                                             "bank": payment.bank_id.bank} if payment.bank_id else None,
                                 "document_type_id": {"id": payment.document_type_id.id,
                                                      "bank": payment.document_type_id.name} if payment.document_type_id else None,
                                 "amount": payment.amount,
                                 "payment_receipt": base64.b64encode(
                                     payment.payment_receipt).decode() if payment.payment_receipt else None
                                 } for payment in transfer.payment_line_ids
                            ]} for transfer in res.transfer_ids
                    ]}
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/ReservationByPipline', type='http', auth='user', csrf=False, methods=['GET'])
    def get_reservation_by_lead(self, id=None, **kwargs):
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

            reservations = request.env['property.reservation'].sudo().search([('crm_lead_id', '=', int(id))])
            data=[]
            if not reservations:
                return request.make_response(
                    json.dumps({"status": 500, "error": "Reservation With the given Lead id doesn't exist"}),
                    headers={'Content-Type': 'application/json'}
                )
            else:
                for res in reservations:
                    data.append( {
                        "id": res.id,
                        "property": {"id": res.property_id.id, "name": res.property_id.name} if res.property_id else None,
                        "site": {"id": res.site_id.id, "name": res.site_id.name} if res.site_id else None,
                        "customer": {"id": res.partner_id.id, "name": res.partner_id.name},
                        "reservation_type": {"id": res.reservation_type_id.id,
                                             "name": res.reservation_type_id.name} if res.reservation_type_id else None,
                        "expire_date": res.expire_date.strftime('%Y-%m-%d %H:%M:%S') if res.expire_date else None,
                        "status": res.status,
                        "is_sufficient": res.is_sufficient,
                        "payment_diff": res.payment_diff,
                        "expected_amount": res.expected_amount,
                        "extension_status": res.extension_status,
                        "transfer_status": res.transfer_status,
                        "payment_lines": [
                            {"id": payment.id,
                             "amount": payment.amount,
                             "status": payment.payment_status}
                            for payment in res.payment_line_ids
                        ],
                        "extensions": [
                            {
                                "id": ext.id,
                                "property_id": res.property_id.id,
                                "old_end_date": ext.old_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                                "extension_date": ext.extension_date.strftime('%Y-%m-%d %H:%M:%S'),
                                "date": ext.create_date.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            for ext in res.extension_ids
                        ],
                        "transfers": [
                            {
                                "id": transfer.id,
                                "date": transfer.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                                "old_property": {"id": transfer.old_property_id.id,
                                                 "name": transfer.old_property_id.name} if transfer.old_property_id else None,
                                "new_property": {"id": transfer.property_id.id,
                                                 "name": transfer.property_id.name} if transfer.property_id else None,
                                "status": transfer.status,
                                "total_paid": transfer.total_paid,
                                "payment_lines": [
                                    {"id": payment.id,
                                     "amount": payment.amount} for payment in transfer.payment_line_ids
                                ]} for transfer in res.transfer_ids
                        ]})
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )


    @http.route('/api/createReservation', type='http', auth='user', csrf=False, methods=['POST'])
    def create_reservation(self, **kwargs):
        """API to create a new property reservation"""

        try:
            # Parse the incoming JSON request
            data = json.loads(request.httprequest.data.decode('utf-8'))
            payment_lines = data.get('payment_line_ids', [])
            for paym in payment_lines:
                ref_number = paym.get('ref_number')
                payments = request.env['property.reservation.payment'].sudo().search([('ref_number', '=', ref_number)])
                for payment in payments:
                    if payment.reservation_id.status not in ['canceled', 'expired']:
                        return request.make_response(
                            json.dumps({"status": 500, "error": f"The Reference Number must be unique. Duplicated  reference  {ref_number}"}),
                            headers={'Content-Type': 'application/json'}
                        )
            # Prepare payment line data for One2many relation
            payment_line_vals = [(0, 0, {
                'payment_receipt': base64.b64decode(payment.get('payment_receipt')) if payment.get(
                'payment_receipt') else False,
                'document_type_id': payment.get('document_type_id'),
                'bank_id': payment.get('bank_id'),
                'ref_number': payment.get('ref_number'),
                'transaction_date': payment.get('transaction_date'),
                'amount': payment.get('amount'),
                'is_verifed': payment.get('is_verifed', False)
            }) for payment in payment_lines]



            # Handle request_letter (Base64 encoded)
            request_letter = base64.b64decode(data.get('request_letter')) if data.get('request_letter') else False

            # Create the reservation record
            request.env['property.reservation'].sudo().create({
                'property_id': data.get('property_id'),
                'partner_id': data.get('partner_id'),
                'crm_lead_id': data.get('lead_id'),
                'salesperson_ids': request.env.user.id,
                'request_letter': request_letter,
                'reservation_type_id': data.get('reservation_type_id'),
                'expire_date': data.get('expire_date'),
                'payment_line_ids': payment_line_vals,
            })

            return request.make_response(
                json.dumps({"status": 200, "message": "Reservation created successfully"}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @http.route('/api/updateReservation', type='http', auth='user', csrf=False, methods=['PUT'])
    def update_reservation(self, **kwargs):
        """API to update an existing CRM lead"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            reservation_id = data.get('id')

            if not reservation_id:
                return request.make_response(
                    json.dumps({"status": 400, "error": "Missing reservation_id"}),
                    headers={'Content-Type': 'application/json'}
                )

            reservation = request.env['property.reservation'].sudo().search([('id', '=', reservation_id)], limit=1)

            if not reservation:
                return request.make_response(
                    json.dumps({"status": 404, "error": "Reservation not found"}),
                    headers={'Content-Type': 'application/json'}
                )

            payment_lines = data.get('payment_line_ids', [])
            payment_line_vals = []

            for payment in payment_lines:
                payment_id = payment.get('id')
                ref_number = payment.get('ref_number')
                payments = request.env['property.reservation.payment'].sudo().search([('ref_number', '=', ref_number)])
                for old_payment in payments:
                    if payment_id != old_payment.id and  old_payment.reservation_id.status not in ['canceled', 'expired']:
                        return request.make_response(
                            json.dumps({"status": 500,
                                        "error": f"The Reference Number must be unique. Duplicated  reference  {ref_number}"}),
                            headers={'Content-Type': 'application/json'}
                        )


                payment_receipt = payment.get('payment_receipt')

                # Ensure payment_receipt is properly encoded
                if payment_receipt and isinstance(payment_receipt, str):
                    payment_receipt_encoded = payment_receipt  # Already base64
                elif payment_receipt:
                    payment_receipt_encoded = base64.b64encode(payment_receipt.read()).decode()
                else:
                    payment_receipt_encoded = False

                payment_data = {
                    'id':payment_id,
                    'payment_receipt': payment_receipt_encoded,
                    'document_type_id': payment.get('document_type_id'),
                    'bank_id': payment.get('bank_id'),
                    'ref_number': payment.get('ref_number'),
                    'transaction_date': payment.get('transaction_date'),
                    'amount': payment.get('amount'),
                    'is_verifed': payment.get('is_verifed', False)
                }

                if payment_id:
                    payment_line_vals.append((1, payment_id, payment_data))  # Update existing
                else:
                    payment_line_vals.append((0, 0, payment_data))  # Create new

            # Handle request_letter safely
            uploaded_file = data.get('request_letter')
            if uploaded_file and isinstance(uploaded_file, str):
                request_letter = uploaded_file  # Already base64
            elif uploaded_file:
                request_letter = base64.b64encode(uploaded_file.read()).decode()
            else:
                request_letter = reservation.request_letter  # Keep existing

            # Update the reservation
            reservation.sudo().write({
                'request_letter': request_letter,
                'property_id': data.get('property_id', reservation.property_id.id),
                'partner_id': data.get('partner_id', reservation.partner_id.id),
                'reservation_type_id': data.get('reservation_type_id', reservation.reservation_type_id.id),
                'expire_date': data.get('expire_date', reservation.expire_date),
                'payment_line_ids': payment_line_vals,
            })

            return request.make_response(
                json.dumps({"status": 200, "message": "Reservation updated successfully"}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )
    @route('/api/getReservationType', type='http', auth='user', csrf=False, methods=['GET'])
    def get_reservation_type(self, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            print("pppppppppppppp: ",session_id)
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

            reservation_types = request.env['property.reservation.configuration'].sudo().search([])

            data = []
            for res in reservation_types:
                data.append({
                    "id": res.id,
                    "name": res.name,
                    "reservation_type": res.reservation_type,
                    "payment_type": res.payment_type,
                    "amount": res.amount,
                    "duration_in": res.duration_in,
                    "duration": res.duration,
                    "is_payment_required": res.is_payment_required,
                    "one_time_use": res.one_time_use,
                    "is_used_use": res.is_used_use
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

    @route('/api/reserve', type='http', auth='user', csrf=False, methods=['GET'])
    def reserve_action(self, id=None, **kwargs):
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

            reservation = request.env['property.reservation'].sudo().search([('id', '=', id)], limit=1)
            if not reservation:
                return request.make_response(
                    json.dumps({"status": 500,
                                "error": "Invalid reservation id"}),
                    headers={'Content-Type': 'application/json'}
                )
            if reservation.property_id.state != 'available':
                return request.make_response(
                    json.dumps({"status": 500,
                                "error": "Cannot approve reservation request. Property %s is in %s state" % (
                                reservation.property_id.name, reservation.property_id.state)}),
                    headers={'Content-Type': 'application/json'}
                )
            reservation.property_id.sudo().write({'state': 'reserved'})
            reservation.write({'status': 'reserved'})
            return request.make_response(
                json.dumps({"status": 200, "massage": "Reservation approved successfully"}),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/cancellationReasons', type='http', auth='user', csrf=False, methods=['GET'])
    def get_cancellation_reasons(self, **kwargs):

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
            reasons = request.env['property.reservation.cancel'].sudo().search([])
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

    @route('/api/cancelReservation', type='http', auth='user', csrf=False, methods=['POST'])
    def cancel_reservation(self, **kwargs):

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
            reservation_id = data.get('reservation_id')
            reason_txt = data.get('reason')
            reason_id = data.get('reason_id')
            if reason_id:
                reason=request.env['property.reservation.cancel'].sudo().search([('id','=',int(reason_id))], limit=1)
                if reason:
                    reason_txt=reason.name


            reservation = request.env['property.reservation'].sudo().search([('id','=',int(reservation_id))])
            if reservation:
                reservation.write({
                    'status': 'canceled',
                    'canceled_time': fields.Datetime.now(),
                    'canceled_reason': reason_txt
                })
                reservation.property_id.write({'state': 'available'})
                stage = request.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
                if stage and reservation.crm_lead_id:
                    reservation.crm_lead_id.write({
                        'stage_id': stage.id,
                    })
            else:
                return request.make_response(
                    json.dumps({"status": 401, "error": "invalid reservation id"}),
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

    @route('/api/deletePayment', type='http', auth='user', csrf=False, methods=['DELETE'])
    def delete_reservation_payment_line(self,**kwargs):
        try:
            # Check if payment_id is provided
            data = json.loads(request.httprequest.data.decode('utf-8'))
            payment_id=data.get('payment_id')
            payment_type=data.get('type')
            if not payment_id:
                return request.make_response(
                    json.dumps({"status": 400, "error": "Missing payment_id"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Check user session
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

            # Search and delete the payment
            if not payment_type=="reservation":
                payment = request.env['property.transfer.payment'].sudo().search([('id', '=', int(payment_id))])
            else:
                payment = request.env['property.reservation.payment'].sudo().search([('id', '=', int(payment_id))])
            if not payment:
                return request.make_response(
                    json.dumps({"status": 404, "error": "Payment record not found"}),
                    headers={'Content-Type': 'application/json'}
                )

            payment.unlink()

            return request.make_response(
                json.dumps({"status": 200, "message": f"Payment with id {payment_id} successfully deleted."}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )





