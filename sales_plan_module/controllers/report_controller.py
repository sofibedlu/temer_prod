# controllers/main.py (updated)
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class SalesPlanReportController(http.Controller):

    @http.route('/sales_plan/get_wing_report', type='json', auth='user', methods=['POST'])
    def get_wing_report(self, **post):
        """Get wing report data via AJAX"""
        try:
            wing_id = int(post.get('wing_id'))
            start_date = post.get('start_date')
            end_date = post.get('end_date')

            _logger.info(f"Generating wing report: {wing_id}, {start_date}, {end_date}")

            # Call the model method
            result = request.env['sales.plan'].get_wing_report_data(
                wing_id,
                start_date,
                end_date
            )

            # Ensure proper JSON serialization
            if 'error' in result:
                return {'success': False, 'error': result['error']}

            return {'success': True, 'data': result}

        except Exception as e:
            _logger.error(f"Error in wing report: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/sales_plan/get_supervisor_report', type='json', auth='user', methods=['POST'])
    def get_supervisor_report(self, **post):
        """Get supervisor report data via AJAX"""
        try:
            supervisor_id = int(post.get('supervisor_id'))
            start_date = post.get('start_date')
            end_date = post.get('end_date')

            _logger.info(f"Generating supervisor report: {supervisor_id}, {start_date}, {end_date}")

            result = request.env['sales.plan'].get_supervisor_report_data(
                supervisor_id,
                start_date,
                end_date
            )

            if 'error' in result:
                return {'success': False, 'error': result['error']}

            return {'success': True, 'data': result}

        except Exception as e:
            _logger.error(f"Error in supervisor report: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/sales_plan/wing_report_page', type='http', auth='user', website=True)
    def wing_report_page(self, **kwargs):
        """Render wing report page"""
        wings = request.env['property.sales.wing'].search([])
        return request.render('sales_plan_module.wing_report_page', {
            'wings': wings,
        })

    @http.route('/sales_plan/supervisor_report_page', type='http', auth='user', website=True)
    def supervisor_report_page(self, **kwargs):
        """Render supervisor report page"""
        supervisors = request.env['property.sales.supervisor'].search([])
        return request.render('sales_plan_module.supervisor_report_page', {
            'supervisors': supervisors,
        })

    class SalesPlanReportController(http.Controller):

        @http.route('/sales_plan/wing_report', type='http', auth='user', website=False)
        def wing_report_page(self, **kwargs):
            """Render wing report page with JavaScript widget"""
            return request.render('sales_plan_module.wing_report_template', {})

        @http.route('/sales_plan/supervisor_report', type='http', auth='user', website=False)
        def supervisor_report_page(self, **kwargs):
            """Render supervisor report page with JavaScript widget"""
            return request.render('sales_plan_module.supervisor_report_template', {})

        @http.route('/sales_plan/get_wings', type='json', auth='user')
        def get_wings(self, **kwargs):
            """Get all wings for dropdown"""
            try:
                wings = request.env['property.sales.wing'].search_read(
                    [], ['id', 'name'], order='name asc'
                )
                return {'success': True, 'wings': wings}
            except Exception as e:
                _logger.error(f"Error getting wings: {e}")
                return {'success': False, 'error': str(e)}

        @http.route('/sales_plan/get_supervisors', type='json', auth='user')
        def get_supervisors(self, **kwargs):
            """Get all supervisors for dropdown"""
            try:
                supervisors = request.env['property.sales.supervisor'].search_read(
                    [], ['id', 'name'], order='name asc'
                )
                # Format for dropdown: [(id, display_name), ...]
                supervisor_list = []
                for sup in supervisors:
                    display_name = sup.get('name', 'Unknown')
                    if isinstance(display_name, list):
                        display_name = display_name[1] if len(display_name) > 1 else 'Unknown'
                    supervisor_list.append({
                        'id': sup['id'],
                        'name': display_name
                    })
                return {'success': True, 'supervisors': supervisor_list}
            except Exception as e:
                _logger.error(f"Error getting supervisors: {e}")
                return {'success': False, 'error': str(e)}

        @http.route('/sales_plan/get_wing_report_data', type='json', auth='user')
        def get_wing_report_data(self, wing_id, start_date, end_date, **kwargs):
            """Get wing report data"""
            try:
                _logger.info(f"Getting wing report: wing_id={wing_id}, start={start_date}, end={end_date}")

                # Call the model method
                result = request.env['sales.plan'].get_wing_report_data(
                    int(wing_id),
                    start_date,
                    end_date
                )

                return {'success': True, 'data': result}
            except Exception as e:
                _logger.error(f"Error in wing report: {e}")
                return {'success': False, 'error': str(e)}

        @http.route('/sales_plan/get_supervisor_report_data', type='json', auth='user')
        def get_supervisor_report_data(self, supervisor_id, start_date, end_date, **kwargs):
            """Get supervisor report data"""
            try:
                _logger.info(
                    f"Getting supervisor report: supervisor_id={supervisor_id}, start={start_date}, end={end_date}")

                # Call the model method
                result = request.env['sales.plan'].get_supervisor_report_data(
                    int(supervisor_id),
                    start_date,
                    end_date
                )

                return {'success': True, 'data': result}
            except Exception as e:
                _logger.error(f"Error in supervisor report: {e}")
                return {'success': False, 'error': str(e)}