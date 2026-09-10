# -*- coding: utf-8 -*-
##############################################################################
#    Property Lock / Unlock
#    Copyright (C) 2024-TODAY Ahadubit Technologies
##############################################################################

from odoo import http
from odoo.http import request
from odoo.addons.ahadubit_property_base.controllers.controllers import PropertyController
import json


class PropertyControllerInherit(PropertyController):

    @http.route('/api/properties', type='http', auth='none', csrf=False, methods=['GET'])
    def get_propertieslist(self, **kwargs):
        """Override: exclude locked properties from API listing for reservation."""
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
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return request.make_response(
                    json.dumps({"status": 401, "error": "Unauthorized: User not found"}),
                    headers={'Content-Type': 'application/json'}
                )
            # Exclude locked properties
            properties = request.env['property.property'].sudo().search([
                ('state', '!=', 'draft'),
                ('is_locked', '=', False)
            ])
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
            return request.make_response(
                json.dumps({"status": 200, "data": data}),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": 500, "error": str(e)}),
                headers={'Content-Type': 'application/json'}
            )
