import json
import logging
import operator

from werkzeug.urls import url_encode

import odoo
import odoo.modules.registry
from odoo import http
from odoo.modules import module
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class CustomAuthController(http.Controller):

    
    @http.route('/web/session/authenticate', type='json', auth="none", csrf=False)
    def authenticate(self, db, login, password, base_location=None):
        # _logger.info("Attempting to authenticate user: %s", login)
        if not http.db_filter([db]):
            _logger.error("Database filter failed for db: %s", db)
            raise AccessError("Database not found.")

        try:
            pre_uid = request.session.authenticate(db, login, password)
            if pre_uid != request.session.uid:
                _logger.warning("Authentication failed for user: %s", login)
                return {'uid': None, 'session_id': None}
        except AccessDenied as e:
            _logger.error("Access denied for user: %s, error: %s", login, str(e))
            raise

        request.session.db = db
        registry = odoo.modules.registry.Registry(db)

        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, request.session.uid, request.session.context)
            
            if not request.db:
                http.root.session_store.rotate(request.session, env)

            session_info = env['ir.http'].session_info()
            
            if not session_info:
                _logger.error("Session information not found for user: %s", login)
                http.abort(500, "Session information not found.")

            # Include session_id in the response body
            session_info.update({
                'session_id': request.session.sid,
            })
            
            # _logger.info("Authentication successful for user: %s", login)
            return session_info
        
        
    # @http.route('/web/session/authenticate', type='json', auth="none", csrf=False)
    # def authenticate(self, db, login, password, base_location=None):
    #     if not http.db_filter([db]):
    #         raise AccessError("Database not found.")

    #     pre_uid = request.session.authenticate(db, login, password)
    #     if pre_uid != request.session.uid:
    #         return {'uid': None, 'session_id': None}

    #     request.session.db = db
    #     registry = odoo.modules.registry.Registry(db)

    #     with registry.cursor() as cr:
    #         env = odoo.api.Environment(cr, request.session.uid, request.session.context)
            
    #         if not request.db:
    #             http.root.session_store.rotate(request.session, env)

    #         session_info = env['ir.http'].session_info()
            
    #         if not session_info:
    #             http.abort(500, "Session information not found.")

    #         # Include session_id in the response body
    #         session_info.update({
    #             'session_id': request.session.sid,
    #         })
            
    #         return session_info
