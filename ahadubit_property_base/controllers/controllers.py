from odoo.http import Controller, request, route
import json
from odoo import http
from odoo.http import request
from bs4 import BeautifulSoup
from datetime import timedelta



class PropertyController(Controller):


    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)

        # Ensure session is fully established before calling session_info
        if not request.session.uid:
            return {"error": "Authentication failed"}

        # Force a new env with correct user
        env = request.env(user=request.session.uid)

        # Use the correct env to get session_info
        response = env['ir.http'].session_info()

        allowed_no_site = int(env['ir.config_parameter'].sudo().get_param(
            'ahadubit_property_base.allows_site_no', default=0))

        response['site'] = {
            'allowed_no_site': allowed_no_site
        }
        return response

    # @http.route('/web/session/authenticate', type='json', auth="none")
    # def authenticate(self, db, login, password, base_location=None):
    #     request.session.authenticate(db, login, password)
    #     response=request.env['ir.http'].session_info()
    #     allowed_no_site = int(request.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.allows_site_no', default=0))

    #     response['site'] = {
    #         'allowed_no_site': allowed_no_site
    #     }
    #     return response

    @route('/api/lookup', type='http', auth='none', csrf=False, methods=['GET'])
    def get_lookup(self,name=None, **kwargs):

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
            if name and name == "site":
                sites = request.env['property.site'].sudo().search([])
                data = []
                for prop in sites:
                    data.append({
                        "id": prop.id,
                        "name": prop.name,

                    })
            elif name and name == "country":
                countries = request.env['res.country'].sudo().search([])
                data = []
                for prop in countries:
                    data.append({
                        "id": prop.id,
                        "phone_code": prop.phone_code,
                        "name": prop.name,

                    })
            elif name and name == "source":
                sources = request.env['utm.source'].sudo().search([])
                data = []
                for prop in sources:
                    data.append({
                        "id": prop.id,
                        "name": prop.name,

                    })
            else:
                return request.make_response(
                    json.dumps({"status": 500, "error": "Please request with valid name => site/country/source"}),
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

    @route('/api/properties', type='http', auth='none', csrf=False, methods=['GET'])
    def get_propertieslist(self, **kwargs):
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
            properties = request.env['property.property'].sudo().search([('state', '!=', 'draft')])

            # Prepare property data for response
            data = []
            for prop in properties:
                data.append({
                    "id": prop.id,
                    "name": prop.name,
                    "property_type": prop.property_type,
                    "site": prop.site.name if prop.site else None,
                    "site_property_type_id": prop.site_property_type_id.property_type_id.code if prop.site_property_type_id else None,
                    "block": prop.block.name if prop.site else None,
                    "floor_id": prop.floor_id.name if prop.floor_id else None,
                    "gross_area": prop.gross_area,
                    "net_area": prop.net_area,
                    "bedroom": prop.bedroom,
                    "bathroom": prop.bathroom,
                    "price": prop.price,
                    "unit_price": prop.unit_price,
                    "state": prop.state,
                    "reservation_end_date": prop.reservation_end_date.strftime('%Y-%m-%d %H:%M:%S') if prop.reservation_end_date else None,
                    "furnishing": prop.furnishing,
                    "finishing": prop.finishing,
                    "country_id": prop.country_id.name if prop.country_id else None,
                    "city": prop.city_id.name if prop.city_id else None,
                    "sub_city_id": prop.sub_city_id.name if prop.sub_city_id else None,
                    "wereda": prop.wereda,
                    "area": prop.area,
                    "street": prop.street,
                    "payment_structure_id": prop.payment_structure_id.name if prop.payment_structure_id else None,
                })

            # Return a successful JSON response
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            # Handle exceptions and return an error response
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    @route('/api/bank', type='http', auth='user', csrf=False, methods=['GET'])
    def get_bank(self, **kwargs):

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
            banks = request.env['bank.configuration'].sudo().search([])
            data = []
            for prop in banks:
                data.append({
                    "id": prop.id,
                    "bank": prop.bank,
                    "account_number": prop.account_number,

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

    @route('/api/documentType', type='http', auth='user', csrf=False, methods=['GET'])
    def get_document_type(self, **kwargs):

        try:
            session_id = request.httprequest.cookies.get('session_id')
            print("session_id: ",session_id)
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
            docs = request.env['bank.document.type'].sudo().search([])
            data = []
            for prop in docs:
                data.append({
                    "id": prop.id,
                    "name": prop.name
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

    @route('/api/checkAmount', type='http', auth='user', csrf=False, methods=['GET'])
    def get_check_amount(self,customer_id=None,reservation_type_id=None,property_id=None, **kwargs):
        try:
            session_id = request.httprequest.cookies.get('session_id')
            print("session_id: ", session_id)
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
            expected = self.compute_expected_amount(reservation_type_id,property_id)
            discount = self.compute_discount_amount(customer_id,property_id)
            expected = expected - (expected * discount)
            data = {
                'expected':expected
            }
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )

    def compute_expected_amount(self,reservation_type_id=False,property_id=False):
        reservation_type=request.env['property.reservation.configuration'].sudo().search([('id','=',reservation_type_id)],limit=1)
        selected_property=request.env['property.property'].sudo().search([('id','=',property_id)],limit=1)
        if reservation_type and  reservation_type.payment_type == "fixed":
            return reservation_type.amount

        # Calculate percentage-based amount
        if selected_property and selected_property.is_multi:
            payment_term_line = request.env['property.payment.term.line'].search(
                [('id', '=', selected_property.site_payment_structure_id.payment_term_id.id)],
                order='sequence', limit=1)
        else:
            payment_term_line = request.env['property.payment.term.line'].search(
                [('id', '=', selected_property.payment_structure_id.id)],
                order='sequence', limit=1)

        expected_per = payment_term_line.percentage if payment_term_line else 0
        base_amount = (selected_property.unit_price
                       if selected_property.sale_rent == "for_sale"
                       else selected_property.rent_month)
        return (base_amount * expected_per / 100) * (reservation_type.amount / 100)

    def compute_discount_amount(self, customer_id,property_id):
        total = 0.0
        selected_property = request.env['property.property'].sudo().search([('id', '=', property_id)], limit=1)
        customer=request.env['res.partner'].sudo().search([('id','=',customer_id)],limit=1)
        if customer and selected_property:
            discounts = request.env['property.special.discount'].search([
                ('partner_id', '=', customer.id),
                ('property_id', '=', selected_property.id),
                ('status', '=', 'approved')
            ])
            for dis in discounts:
                total += dis.discount

        return total

    @route('/api/general', type='http', auth='user', csrf=False, methods=['GET'])
    def get_general(self, customer_id=None, reservation_type_id=None, property_id=None, **kwargs):
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
            channel = request.env['discuss.channel'].sudo().search([('name', '=', 'general')], limit=1)
            if not channel:
                return request.make_response(
                    json.dumps({"status": 500, "error": "Channel not found"}),
                    headers={'Content-Type': 'application/json'}
                )

            # Fetch messages linked to this channel
            messages = request.env['mail.message'].sudo().search([
                ('model', '=', 'discuss.channel'),
                ('res_id', '=', channel.id)
            ], order="create_date DESC")  # Fetch the last 10 messages
            # Format the messages
            result = []
            for message in messages:
                create_date=message.create_date+timedelta(hours=3)
                result.append({
                    'id': message.id,
                    'message': BeautifulSoup(message.body, 'html.parser').get_text() if message.body else "",
                    'user': {"id":message.author_id.id, "name": message.author_id.name} if message.author_id else None,
                    'date':create_date.strftime('%Y-%m-%d %H:%M:%S') if message.create_date else None,
                })

            return request.make_response(
                json.dumps({"status": 200, "data": result}),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )



