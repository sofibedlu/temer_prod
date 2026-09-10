from odoo.http import Controller, request, route
import json
from odoo import http
from odoo.http import request
from bs4 import BeautifulSoup
import base64



class extensionController(Controller):

    @route('/api/extension', type='http', auth='none', csrf=False, methods=['GET'])
    def get_extension(self, **kwargs):

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
            sites = request.env['property.reservation.extend.history'].sudo().search([])
            data = []
            for prop in sites:
                data.append({
                    "id": prop.id,
                    "reservation_id": prop.reservation_id.id if prop.reservation_id else None,
                    "status": prop.status,
                    "extension_date": prop.extension_date.strftime('%Y-%m-%d %H:%M:%S') if prop.extension_date else None,
                    "old_end_date":prop.old_end_date.strftime('%Y-%m-%d %H:%M:%S') if prop.old_end_date else None,
                    "request_letter_file": base64.b64encode( prop.request_letter_file).decode() if  prop.request_letter_file else None,
                    "remark": prop.remark,

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

    @route('/api/extensionByReservation', type='http', auth='none', csrf=False, methods=['GET'])
    def get_extension_by_reservation(self, reservation_id=None, **kwargs):

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
            sites = request.env['property.reservation.extend.history'].sudo().search([('reservation_id','=',int(reservation_id))])
            data = []
            for prop in sites:
                data.append({
                    "id": prop.id,
                    "reservation_id": prop.reservation_id.id if prop.reservation_id else None,
                    "status": prop.status,
                    "extension_date": prop.extension_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if prop.extension_date else None,
                    "old_end_date": prop.old_end_date.strftime('%Y-%m-%d %H:%M:%S') if prop.old_end_date else None,
                    "request_letter_file": base64.b64encode(
                        prop.request_letter_file).decode() if prop.request_letter_file else None,
                    "remark": prop.remark,

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

    @route('/api/createExtension', type='json', auth='user', csrf=False, methods=['POST'])
    def create_extension(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            required_fields = ['reservation_id', 'extension_date', 'request_letter_file', 'remark']
            if not all(field in data for field in required_fields):
                return {"status": 400, "error": "Missing required fields"}

            uploaded_file = data.get('request_letter_file')
            if uploaded_file and isinstance(uploaded_file, str):
                request_letter = uploaded_file  # Already base64
            elif uploaded_file:
                request_letter = base64.b64encode(uploaded_file.read()).decode()
            else:
                request_letter = False  # Keep existing

            new_record = request.env['property.reservation.extend.history'].sudo().create({
                'reservation_id': data.get('reservation_id'),
                'extension_date': data.get('extension_date'),
                'old_end_date': data.get('old_end_date'),
                'remark': data.get('remark'),
                'request_letter_file': request_letter,
            })
            return {"status": 201, "message": "Record created successfully", "id": new_record.id}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    @route('/api/updateExtension', type='json', auth='user', csrf=False, methods=['PUT'])
    def update_extension(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            extension_id = data.get('id')
            if not extension_id:
                return request.make_response(
                    json.dumps({"status": 400, "error": "Missing id"}),
                    headers={'Content-Type': 'application/json'}
                )
            extension = request.env['property.reservation.extend.history'].sudo().search([('id', '=', extension_id)], limit=1)
            if not extension:
                return request.make_response(
                    json.dumps({"status": 404, "error": "Extension not found"}),
                    headers={'Content-Type': 'application/json'}
                )
            uploaded_file = data.get('request_letter_file')
            if uploaded_file and isinstance(uploaded_file, str):
                request_letter = uploaded_file  # Already base64
            elif uploaded_file:
                request_letter = base64.b64encode(uploaded_file.read()).decode()
            else:
                request_letter = extension.request_letter_file
            extension.sudo().write({
                'reservation_id': data.get('reservation_id', extension.reservation_id.id),
                'extension_date': data.get('extension_date', extension.extension_date),
                'old_end_date': data.get('old_end_date', extension.old_end_date),
                'remark': data.get('remark', extension.remark),
                'request_letter_file': request_letter,

            })
            return {"status": 201, "message": "Record updated successfully"}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    @route('/api/transfers', type='http', auth='none', csrf=False, methods=['GET'])
    def get_transfer(self, **kwargs):

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
            transfers = request.env['property.reservation.transfer.history'].sudo().search([])
            data = []
            for res in transfers:
                data.append({
                    "id": res.id,
                    "reservation_id": res.reservation_id.id if res.reservation_id else None,
                    "old_property_id": {"id": res.old_property_id.id,
                                        "name": res.old_property_id.name} if res.old_property_id else None,
                    "property_id": {"id": res.property_id.id,
                                    "name": res.property_id.name} if res.property_id else None,
                    "status": res.status,
                    "request_letter": base64.b64encode(res.request_letter).decode() if res.request_letter else None,
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
                         }
                        for payment in res.payment_line_ids
                    ]
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

    @route('/api/transferByReservation', type='http', auth='none', csrf=False, methods=['GET'])
    def get_transfer_by_reservation(self, reservation_id=None, **kwargs):

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
            transfers = request.env['property.reservation.transfer.history'].sudo().search(
                [('reservation_id', '=', int(reservation_id))])
            data = []
            for res in transfers:
                data.append({
                    "id": res.id,
                    "reservation_id": res.reservation_id.id if res.reservation_id else None,
                    "old_property_id": {"id": res.old_property_id.id,
                                        "name": res.old_property_id.name} if res.old_property_id else None,
                    "property_id": {"id": res.property_id.id,
                                    "name": res.property_id.name} if res.property_id else None,
                    "status": res.status,
                    "request_letter": base64.b64encode(res.request_letter).decode() if res.request_letter else None,
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
                         }
                        for payment in res.payment_line_ids
                    ]
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

    @route('/api/myTransferRequests', type='http', auth='user', csrf=False, methods=['GET'])
    def get_transfer_requests(self, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            print("ppppppppppppppppppppppppppppppppppppp: ",session_id)
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

            transfers = request.env['property.reservation.transfer.history'].sudo().search([('create_uid','=',user_id)])
            data = []
            for res in transfers:
                data.append({
                    "id": res.id,
                    "reservation_id": res.reservation_id.id if res.reservation_id else None,
                    "old_property_id": {"id": res.old_property_id.id,
                                        "name": res.old_property_id.name} if res.old_property_id else None,
                    "property_id": {"id": res.property_id.id,
                                    "name": res.property_id.name} if res.property_id else None,
                    "status": res.status,
                    "request_letter":base64.b64encode(res.request_letter).decode() if res.request_letter else None,
                    "payment_lines": [
                        {"id": payment.id,
                         "ref_number": payment.ref_number,
                         "bank_id":{"id": payment.bank_id.id,
                                        "bank": payment.bank_id.bank} if payment.bank_id else None,
                         "document_type_id":{"id": payment.document_type_id.id,
                                        "bank": payment.document_type_id.name} if payment.document_type_id else None,
                         "amount": payment.amount,
                         "payment_receipt": base64.b64encode(payment.payment_receipt).decode() if payment.payment_receipt else None
                         }
                        for payment in res.payment_line_ids
                    ]
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

    @route('/api/createTransfer', type='json', auth='user', csrf=False, methods=['POST'])
    def create_transfer(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            payment_lines = data.get('payment_line_ids', [])
            for paym in payment_lines:
                ref_number = paym.get('ref_number')
                payments = request.env['property.transfer.payment'].sudo().search([('ref_number', '=', ref_number)])
                for payment in payments:
                    if payment.transfer_id.status not in ['rejected']:
                        return {"status": 201, "message": f"The Reference Number must be unique. Duplicated  reference  {ref_number}"}
            # Prepare payment line data for One2many relation
            payment_line_vals = [(0, 0, {
                'payment_receipt': base64.b64decode(payment.get('payment_receipt')) if payment.get(
                    'payment_receipt') else False,
                'document_type_id': payment.get('document_type_id'),
                'bank_id': payment.get('bank_id'),
                'ref_number': payment.get('ref_number'),
                'transaction_date': payment.get('transaction_date'),
                'amount': payment.get('amount'),
                'id_editable': False,
            }) for payment in payment_lines]


            reservation_id = int(data.get('reservation_id'))
            reservation = request.env['property.reservation'].sudo().search([('id', '=', reservation_id)])
            if reservation and reservation.transfer_status != "pending":
                request_letter = base64.b64decode(data.get('request_letter')) if data.get('request_letter') else False
                new_record = request.env['property.reservation.transfer.history'].sudo().create({
                    'reservation_id': data.get('reservation_id'),
                    'old_property_id': data.get('old_property_id'),
                    'property_id': data.get('property_id'),
                    'request_letter': request_letter,
                    "payment_line_ids":payment_line_vals
                })
            else:
                return {"status": 201, "message": "There is pending transfer request for this reservation "}

            return {"status": 201, "message": "Record created successfully", "id": new_record.id}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    @http.route('/api/updateTransfer', type='http', auth='user', csrf=False, methods=['PUT'])
    def update_transfer(self, **kwargs):
        """API to update an existing CRM lead"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            transfer_id = data.get('id')

            if not transfer_id:
                return request.make_response(
                    json.dumps({"status": 400, "error": "Missing id"}),
                    headers={'Content-Type': 'application/json'}
                )

            transfer = request.env['property.reservation.transfer.history'].sudo().search([('id', '=', transfer_id)], limit=1)

            if not transfer:
                return {"status": 201, "message": "Reservation not found"}


            payment_lines = data.get('payment_line_ids', [])
            payment_line_vals = []

            for payment in payment_lines:
                payment_id = payment.get('id')
                ref_number = payment.get('ref_number')
                payments = request.env['property.transfer.payment'].sudo().search([('ref_number', '=', ref_number)])
                for old_payment in payments:
                    if payment_id != old_payment.id and old_payment.transfer_id.status not in ['rejected']:
                        return {"status": 500, "message":  f"The Reference Number must be unique. Duplicated  reference  {ref_number}"}


                payment_receipt = payment.get('payment_receipt')

                # Ensure payment_receipt is properly encoded
                if payment_receipt and isinstance(payment_receipt, str):
                    payment_receipt_encoded = payment_receipt  # Already base64
                elif payment_receipt:
                    payment_receipt_encoded = base64.b64encode(payment_receipt.read()).decode()
                else:
                    payment_receipt_encoded = False

                payment_data = {
                    'payment_receipt': payment_receipt_encoded,
                    'document_type_id': payment.get('document_type_id'),
                    'bank_id': payment.get('bank_id'),
                    'ref_number': payment.get('ref_number'),
                    'transaction_date': payment.get('transaction_date'),
                    'amount': payment.get('amount'),
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
                request_letter = transfer.request_letter  # Keep existing

            # Update the reservation
            transfer.sudo().write({
                'reservation_id': data.get('reservation_id',transfer.reservation_id.id),
                'old_property_id': data.get('old_property_id',transfer.old_property_id.id),
                'property_id': data.get('property_id',transfer.property_id.id),
                'request_letter': request_letter,
                'payment_line_ids': payment_line_vals,
            })

            return request.make_response(
                json.dumps({"status": 200, "message": "Transfer updated successfully"}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )


