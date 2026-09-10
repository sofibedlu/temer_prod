# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class SalesReportController(http.Controller):
    
    def _get_wing_name_for_user(self, user):
        """Get the wing name for a supervisor, sales manager, or wing manager.
        For Sales Managers, returns format: "Team - {WingName}"
        For others, returns just the wing name.
        Same logic as sales_plan_module Plan Document.
        """
        env = request.env
        
        # Check if user is wing manager
        env.cr.execute("SELECT id, name FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
        wing_manager_result = env.cr.fetchone()
        if wing_manager_result:
            return wing_manager_result[1]  # Just wing name for wing managers
        
        # Check if user is team manager (Sales Manager)
        env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        team_result = env.cr.fetchone()
        
        if team_result:
            # Sales Manager - return "Team - {WingName}" format
            team_id = team_result[0]
            env.cr.execute("""
                SELECT DISTINCT w.id, w.name
                FROM property_sales_team t
                LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                WHERE t.id = %s AND w.id IS NOT NULL
                LIMIT 1
            """, (team_id,))
            wing_result = env.cr.fetchone()
            if wing_result:
                wing_name = wing_result[1]
                return f"Team - {wing_name}"  # Format: "Team - Raha"
        
        return None

    @http.route('/sales_plan_report/api/get_wings', type='json', auth='user', methods=['POST'], csrf=False)
    def api_get_wings(self, **kwargs):
        """API endpoint to get wings - filtered by user role (managers only)"""
        try:
            user = request.env.user
            
            # Check if user is manager, CRM Admin, or system admin
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_manager_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            
            is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            # Only managers, CRM Admin, and system admins can access
            is_manager_or_admin = bool(wing_manager_result or team_result or is_crm_admin)
            if not is_manager_or_admin and not is_system_admin:
                return {
                    'success': False,
                    'error': 'Access Denied: Only Sales Manager Admin, Sales Managers, and Wing Managers can view this report.',
                    'wings': [],
                }
            
            # Filter wings based on role
            if wing_manager_result:
                # Wing Manager: Only their wing
                wing_id = wing_manager_result[0]
                wings = request.env['property.sales.wing'].browse([wing_id])
            elif team_result:
                # Sales Manager: Wings in their team
                team_id = team_result[0]
                env.cr.execute("""
                    SELECT DISTINCT w.id
                    FROM property_sales_team t
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    WHERE t.id = %s AND w.id IS NOT NULL
                """, (team_id,))
                wing_ids = [r[0] for r in env.cr.fetchall()]
                wings = request.env['property.sales.wing'].browse(wing_ids) if wing_ids else request.env['property.sales.wing']
            else:
                # CRM Admin or System Admin: All wings
                wings = request.env['property.sales.wing'].search([])
            
            wings_data = []
            for wing in wings:
                wings_data.append({
                    'id': wing.id,
                    'name': wing.name or '',
                })
            wings_data.sort(key=lambda x: x['name'])
            return {
                'success': True,
                'wings': wings_data,
            }
        except Exception as e:
            _logger.error(f"Error in get_wings API: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'wings': [],
            }
    
    def _get_supervisor_ids_for_role(self, user):
        """
        Get supervisor IDs based on user's role (same logic as sales_plan_module Plan Document).
        Hierarchy: Wing Manager -> Sales Manager -> Supervisor
        Returns list of supervisor IDs that the manager can see reports for.
        """
        supervisor_ids = []
        env = request.env
        
        # Check if user is admin
        is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
        
        # Check if user is wing manager
        env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
        wing_manager_result = env.cr.fetchone()
        
        # Check if user is team manager (sales manager)
        env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        team_result = env.cr.fetchone()
        
        if wing_manager_result:
            # Wing Manager: Get all supervisors in their wing
            wing_id = wing_manager_result[0]
            env.cr.execute("""
                SELECT DISTINCT t.id
                FROM property_sales_wing w
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                WHERE w.id = %s AND t.id IS NOT NULL
            """, (wing_id,))
            team_ids = [r[0] for r in env.cr.fetchall()]
            
            if team_ids:
                env.cr.execute("""
                    SELECT DISTINCT s.id
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    WHERE t.id IN %s AND s.id IS NOT NULL
                """, (tuple(team_ids),))
                supervisor_ids = [r[0] for r in env.cr.fetchall()]
        
        elif team_result:
            # Sales Manager: Get supervisors in their team
            team_id = team_result[0]
            env.cr.execute("""
                SELECT DISTINCT s.id
                FROM property_sales_team t
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                WHERE t.id = %s AND s.id IS NOT NULL
            """, (team_id,))
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
        
        # Check if user is CRM Admin (Sales Manager Admin)
        is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
        if is_crm_admin and not wing_manager_result and not team_result:
            # CRM Admin: Get all supervisors
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE id IS NOT NULL")
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
        
        if is_admin and not wing_manager_result and not team_result:
            # System Admin: Get all supervisors
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE id IS NOT NULL")
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
        
        return list(set(supervisor_ids))

    @http.route('/sales_plan_report/api/get_supervisors', type='json', auth='user', methods=['POST'], csrf=False)
    def api_get_supervisors(self, **kwargs):
        """API endpoint to get supervisors - filtered by user role (managers only)"""
        try:
            user = request.env.user
            
            # Check if user is manager, CRM Admin, or system admin
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_manager_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            
            is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            # Only managers, CRM Admin, and system admins can access
            is_manager_or_admin = bool(wing_manager_result or team_result or is_crm_admin)
            if not is_manager_or_admin and not is_system_admin:
                return {
                    'success': False,
                    'error': 'Access Denied: Only Sales Manager Admin, Sales Managers, and Wing Managers can view this report.',
                    'supervisors': [],
                }
            
            # Get supervisor IDs based on role
            supervisor_ids = self._get_supervisor_ids_for_role(user)
            
            if not supervisor_ids:
                return {
                    'success': True,
                    'supervisors': [],
                }
            
            supervisors = request.env['property.sales.supervisor'].browse(supervisor_ids)
            supervisors_data = []
            for supervisor in supervisors:
                supervisors_data.append({
                    'id': supervisor.id,
                    'name': supervisor.name.name if supervisor.name else '',
                })
            supervisors_data.sort(key=lambda x: x['name'])
            return {
                'success': True,
                'supervisors': supervisors_data,
            }
        except Exception as e:
            _logger.error(f"Error in get_supervisors API: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'supervisors': [],
            }
    
    @http.route('/sales_plan_report/api/sales_report', type='json', auth='user', methods=['POST'], csrf=False)
    def api_sales_report(self, **kwargs):
        """API endpoint for Sales Performance Report data - Only for managers (Sales Manager/Wing Manager/CRM Admin)"""
        try:
            user = request.env.user
            
            # Check if user is manager, CRM Admin, or system admin
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_manager_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            
            is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            # Only managers, CRM Admin, and system admins can access
            is_manager_or_admin = bool(wing_manager_result or team_result or is_crm_admin)
            if not is_manager_or_admin and not is_system_admin:
                return {
                    'success': False,
                    'error': 'Access Denied: Only Sales Manager Admin, Sales Managers, and Wing Managers can view this report.',
                    'data': {},
                    'role_display': '',
                    'selected_wing_name': '',
                }
            
            # Determine user role and wing name early (before any early returns)
            role_display = ''
            selected_wing_name = None
            
            # Get wing name for user
            wing_name = self._get_wing_name_for_user(user)
            if wing_name:
                selected_wing_name = wing_name
            
            # Determine role display
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result = env.cr.fetchone()
            
            if is_system_admin:
                if team_result:
                    role_display = 'Admin - Sales Manager'
                elif supervisor_result:
                    role_display = 'Admin - Supervisor'
                else:
                    role_display = 'Admin'
            else:
                if wing_manager_result:
                    role_display = 'Wing Manager'
                elif team_result:
                    role_display = 'Sales Manager'
                elif supervisor_result:
                    role_display = 'Supervisor'
                elif is_crm_admin:
                    role_display = 'Sales Manager Admin'
                else:
                    role_display = 'User'
            
            # Get filters from request
            params = kwargs.get('params', {}) if isinstance(kwargs.get('params'), dict) else kwargs
            report_type = params.get('report_type') or kwargs.get('report_type')
            wing_id = params.get('wing_id') or kwargs.get('wing_id')
            supervisor_id = params.get('supervisor_id') or kwargs.get('supervisor_id')
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            
            # Convert date strings to datetime objects
            if date_from and date_from != 'null' and date_from:
                try:
                    date_from = fields.Date.from_string(date_from)
                except:
                    date_from = None
            else:
                date_from = None
            if date_to and date_to != 'null' and date_to:
                try:
                    date_to = fields.Date.from_string(date_to)
                except:
                    date_to = None
            else:
                date_to = None
            
            if not date_from or not date_to:
                return {
                    'success': False,
                    'error': 'Date range is required',
                    'data': {},
                    'role_display': role_display,
                    'selected_wing_name': selected_wing_name or '',
                }
            
            # Create a temporary sales.report record to use its methods
            report_vals = {
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
            }
            if report_type == 'wing' and wing_id:
                report_vals['wing_id'] = int(wing_id)
            elif report_type == 'supervisor' and supervisor_id:
                report_vals['supervisor_id'] = int(supervisor_id)
            
            # Create report record - use the returned record directly, don't re-fetch
            # This avoids "Record does not exist" errors on server
            try:
                report = request.env['sales.report'].create(report_vals)
                # The create method already calls _generate_report() if conditions are met
                # Use the record directly - don't re-fetch with browse() as it can cause issues
                _logger.info(f"Created sales.report record with ID: {report.id}")
            except Exception as create_error:
                _logger.error(f"Error creating report record: {str(create_error)}", exc_info=True)
                return {
                    'success': False,
                    'error': f'Failed to create report: {str(create_error)}',
                }
            
            # Ensure report data is generated if it wasn't auto-generated
            try:
                # Check if report was populated (if _generate_report ran during create)
                # If not, generate it now
                if (getattr(report, 'actual_prospects', 0) == 0 and 
                    getattr(report, 'plan_prospects', 0) == 0 and 
                    getattr(report, 'actual_follow_ups', 0) == 0):
                    _logger.info("Report appears empty, calling _generate_report() manually")
                    report._generate_report()
            except Exception as gen_error:
                _logger.warning(f"Error in _generate_report: {str(gen_error)}", exc_info=True)
                # Continue - use whatever data we have
            
            # Get computed fields with safe access
            try:
                conversion_rate = getattr(report, 'conversion_rate', 0.0) or 0.0
            except:
                conversion_rate = 0.0
            
            try:
                iar_rate = getattr(report, 'iar_rate', 0.0) or 0.0
            except:
                iar_rate = 0.0
            
            # Return report data - use safe access with getattr and defaults
            # Helper function to safely get field value
            def safe_get(record, field_name, default=0):
                """Safely get field value, return default if field access fails"""
                try:
                    value = getattr(record, field_name, default)
                    return value if value is not None else default
                except Exception as e:
                    _logger.warning(f"Error accessing field {field_name}: {str(e)}")
                    return default
            
            try:
                # Use the record directly - don't re-fetch to avoid "Record does not exist" errors
                return {
                    'success': True,
                    'data': {
                        'actual_previous_week_prospects': safe_get(report, 'actual_previous_week_prospects', 0),
                        'plan_prospects': safe_get(report, 'plan_prospects', 0),
                        'actual_prospects': safe_get(report, 'actual_prospects', 0),
                        'diff_week_prospects': safe_get(report, 'diff_week_prospects', 0),
                        'diff_prospects': safe_get(report, 'diff_prospects', 0),
                        'percent_prospects': safe_get(report, 'percent_prospects', 0.0),
                        'actual_previous_week_follow_ups': safe_get(report, 'actual_previous_week_follow_ups', 0),
                        'plan_follow_ups': safe_get(report, 'plan_follow_ups', 0),
                        'actual_follow_ups': safe_get(report, 'actual_follow_ups', 0),
                        'diff_week_follow_ups': safe_get(report, 'diff_week_follow_ups', 0),
                        'diff_follow_ups': safe_get(report, 'diff_follow_ups', 0),
                        'percent_follow_ups': safe_get(report, 'percent_follow_ups', 0.0),
                        'actual_previous_week_site_visits': safe_get(report, 'actual_previous_week_site_visits', 0),
                        'plan_site_visits': safe_get(report, 'plan_site_visits', 0),
                        'actual_site_visits': safe_get(report, 'actual_site_visits', 0),
                        'diff_week_site_visits': safe_get(report, 'diff_week_site_visits', 0),
                        'diff_site_visits': safe_get(report, 'diff_site_visits', 0),
                        'percent_site_visits': safe_get(report, 'percent_site_visits', 0.0),
                        'actual_previous_week_office_visits': safe_get(report, 'actual_previous_week_office_visits', 0),
                        'plan_office_visits': safe_get(report, 'plan_office_visits', 0),
                        'actual_office_visits': safe_get(report, 'actual_office_visits', 0),
                        'diff_week_office_visits': safe_get(report, 'diff_week_office_visits', 0),
                        'diff_office_visits': safe_get(report, 'diff_office_visits', 0),
                        'percent_office_visits': safe_get(report, 'percent_office_visits', 0.0),
                        'actual_previous_week_total_visits': safe_get(report, 'actual_previous_week_total_visits', 0),
                        'plan_total_visits': safe_get(report, 'plan_total_visits', 0),
                        'actual_total_visits': safe_get(report, 'actual_total_visits', 0),
                        'diff_week_total_visits': safe_get(report, 'diff_week_total_visits', 0),
                        'diff_total_visits': safe_get(report, 'diff_total_visits', 0),
                        'percent_total_visits': safe_get(report, 'percent_total_visits', 0.0),
                        'actual_previous_week_unit_reservations': safe_get(report, 'actual_previous_week_unit_reservations', 0),
                        'plan_unit_reservations': safe_get(report, 'plan_unit_reservations', 0),
                        'actual_unit_reservations': safe_get(report, 'actual_unit_reservations', 0),
                        'diff_week_unit_reservations': safe_get(report, 'diff_week_unit_reservations', 0),
                        'diff_unit_reservations': safe_get(report, 'diff_unit_reservations', 0),
                        'percent_unit_reservations': safe_get(report, 'percent_unit_reservations', 0.0),
                        'actual_previous_week_deals_closed': safe_get(report, 'actual_previous_week_deals_closed', 0),
                        'plan_deals_closed': safe_get(report, 'plan_deals_closed', 0),
                        'actual_deals_closed': safe_get(report, 'actual_deals_closed', 0),
                        'diff_week_deals_closed': safe_get(report, 'diff_week_deals_closed', 0),
                        'diff_deals_closed': safe_get(report, 'diff_deals_closed', 0),
                        'percent_deals_closed': safe_get(report, 'percent_deals_closed', 0.0),
                        'conversion_rate': conversion_rate,
                        'actual_previous_week_conversion_rate': safe_get(report, 'actual_previous_week_conversion_rate', 0.0),
                        'plan_conversion_rate': safe_get(report, 'plan_conversion_rate', 0.0),
                        'diff_week_conversion_rate': safe_get(report, 'diff_week_conversion_rate', 0.0),
                        'diff_conversion_rate': safe_get(report, 'diff_conversion_rate', 0.0),
                        'percent_conversion_rate': safe_get(report, 'percent_conversion_rate', 0.0),
                        'actual_previous_week_cash_collected': safe_get(report, 'actual_previous_week_cash_collected', 0.0),
                        'plan_cash_collected': safe_get(report, 'plan_cash_collected', 0.0),
                        'actual_cash_collected': safe_get(report, 'actual_cash_collected', 0.0),
                        'diff_week_cash_collected': safe_get(report, 'diff_week_cash_collected', 0.0),
                        'diff_cash_collected': safe_get(report, 'diff_cash_collected', 0.0),
                        'percent_cash_collected': safe_get(report, 'percent_cash_collected', 0.0),
                        'actual_previous_week_total_deal_value': safe_get(report, 'actual_previous_week_total_deal_value', 0.0),
                        'plan_total_deal_value': safe_get(report, 'plan_total_deal_value', 0.0),
                        'actual_total_deal_value': safe_get(report, 'actual_total_deal_value', 0.0),
                        'diff_week_total_deal_value': safe_get(report, 'diff_week_total_deal_value', 0.0),
                        'diff_total_deal_value': safe_get(report, 'diff_total_deal_value', 0.0),
                        'percent_total_deal_value': safe_get(report, 'percent_total_deal_value', 0.0),
                        'opening_stock_residence_qty': safe_get(report, 'opening_stock_residence_qty', 0),
                        'opening_stock_residence_value': safe_get(report, 'opening_stock_residence_value', 0.0),
                        'opening_stock_shops_qty': safe_get(report, 'opening_stock_shops_qty', 0),
                        'opening_stock_shops_value': safe_get(report, 'opening_stock_shops_value', 0.0),
                        'opening_stock_total_qty': safe_get(report, 'opening_stock_total_qty', 0),
                        'opening_stock_total_value': safe_get(report, 'opening_stock_total_value', 0.0),
                        'plan_opening_stock_residence_qty': safe_get(report, 'plan_opening_stock_residence_qty', 0),
                        'plan_opening_stock_residence_value': safe_get(report, 'plan_opening_stock_residence_value', 0.0),
                        'plan_opening_stock_shops_qty': safe_get(report, 'plan_opening_stock_shops_qty', 0),
                        'plan_opening_stock_shops_value': safe_get(report, 'plan_opening_stock_shops_value', 0.0),
                        'plan_opening_stock_total_qty': safe_get(report, 'plan_opening_stock_total_qty', 0),
                        'plan_opening_stock_total_value': safe_get(report, 'plan_opening_stock_total_value', 0.0),
                        'actual_previous_week_iar_rate': safe_get(report, 'actual_previous_week_iar_rate', 0.0),
                        'plan_iar_rate': safe_get(report, 'plan_iar_rate', 0.0),
                        'diff_week_iar_rate': safe_get(report, 'diff_week_iar_rate', 0.0),
                        'diff_iar_rate': safe_get(report, 'diff_iar_rate', 0.0),
                        'percent_iar_rate': safe_get(report, 'percent_iar_rate', 0.0),
                        'iar_rate': iar_rate,
                    },
                    'role_display': role_display,
                    'selected_wing_name': selected_wing_name or '',
                }
            except Exception as field_error:
                _logger.error(f"Error accessing report fields: {str(field_error)}", exc_info=True)
                # If record was deleted, return error with more context
                error_msg = str(field_error)
                if 'does not exist' in error_msg or 'has been deleted' in error_msg or 'MissingError' in str(type(field_error)):
                    return {
                        'success': False,
                        'error': f'Report record was deleted or does not exist. Please try again.',
                        'data': {},
                        'role_display': role_display,
                        'selected_wing_name': selected_wing_name or '',
                    }
                raise  # Re-raise if it's a different error
        except Exception as e:
            _logger.error(f"Error in sales_report API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'role_display': role_display if 'role_display' in locals() else '',
                'selected_wing_name': selected_wing_name if 'selected_wing_name' in locals() else '',
            }
    
    @http.route('/sales_plan_report/api/export_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def export_excel(self, **kwargs):
        """Export report to Excel"""
        try:
            report_type = kwargs.get('report_type')
            wing_id = kwargs.get('wing_id')
            supervisor_id = kwargs.get('supervisor_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            if date_from:
                date_from = fields.Date.from_string(date_from)
            if date_to:
                date_to = fields.Date.from_string(date_to)
            
            report_vals = {
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
            }
            if report_type == 'wing' and wing_id:
                report_vals['wing_id'] = int(wing_id)
            elif report_type == 'supervisor' and supervisor_id:
                report_vals['supervisor_id'] = int(supervisor_id)
            
            report = request.env['sales.report'].create(report_vals)
            
            # Ensure report data is generated
            report._generate_report()

            # Build XLSX with table borders
            import io
            import xlsxwriter
            from odoo.http import Response

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Sales Report')

            header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9E1F2', 'align': 'center'})
            cell_fmt = workbook.add_format({'border': 1})
            num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
            pct_fmt = workbook.add_format({'border': 1, 'num_format': '0.00'})

            headers = ['Metric', 'Actual Previous Week', 'Plan', 'Actual',
                       'Difference (This week - Previous week)', 'Difference (Actual - Plan)', '% Achievement']
            worksheet.write_row(0, 0, headers, header_fmt)

            data_rows = [
                ['Prospects (Leads)', report.actual_previous_week_prospects, report.plan_prospects,
                 report.actual_prospects, report.diff_week_prospects, report.diff_prospects, report.percent_prospects],
                ['Follow-ups', report.actual_previous_week_follow_ups, report.plan_follow_ups,
                 report.actual_follow_ups, report.diff_week_follow_ups, report.diff_follow_ups, report.percent_follow_ups],
                ['Site Visits', report.actual_previous_week_site_visits, report.plan_site_visits,
                 report.actual_site_visits, report.diff_week_site_visits, report.diff_site_visits, report.percent_site_visits],
                ['Office Visits', report.actual_previous_week_office_visits, report.plan_office_visits,
                 report.actual_office_visits, report.diff_week_office_visits, report.diff_office_visits, report.percent_office_visits],
                ['Total Visits (Site + Office)', report.actual_previous_week_total_visits, report.plan_total_visits,
                 report.actual_total_visits, report.diff_week_total_visits, report.diff_total_visits, report.percent_total_visits],
                ['Total unit reservations', report.actual_previous_week_unit_reservations, report.plan_unit_reservations,
                 report.actual_unit_reservations, report.diff_week_unit_reservations, report.diff_unit_reservations, report.percent_unit_reservations],
                ['Deals Closed (QTY)', report.actual_previous_week_deals_closed, report.plan_deals_closed,
                 report.actual_deals_closed, report.diff_week_deals_closed, report.diff_deals_closed, report.percent_deals_closed],
                ['Conversion (sales/leads)', report.actual_previous_week_conversion_rate, report.plan_conversion_rate,
                 report.conversion_rate, report.diff_week_conversion_rate, report.diff_conversion_rate, report.percent_conversion_rate],
                ['Cash Collected (Birr)', report.actual_previous_week_cash_collected, report.plan_cash_collected,
                 report.actual_cash_collected, report.diff_week_cash_collected, report.diff_cash_collected, report.percent_cash_collected],
                ['Total Deal Value (Birr)', report.actual_previous_week_total_deal_value, report.plan_total_deal_value,
                 report.actual_total_deal_value, report.diff_week_total_deal_value, report.diff_total_deal_value, report.percent_total_deal_value],
                ['IAR (sales/opening stock)', report.actual_previous_week_iar_rate, report.plan_iar_rate,
                 report.iar_rate, report.diff_week_iar_rate, report.diff_iar_rate, report.percent_iar_rate],
            ]

            row_idx = 1
            for row in data_rows:
                worksheet.write(row_idx, 0, row[0], cell_fmt)
                for col in range(1, 6):
                    worksheet.write(row_idx, col, row[col], num_fmt)
                worksheet.write(row_idx, 6, row[6], pct_fmt)
                row_idx += 1

            # Opening Stock table
            row_idx += 2
            worksheet.write(row_idx, 0, 'Opening Stock (Plan)', header_fmt)
            row_idx += 1
            worksheet.write_row(row_idx, 0, ['Type', 'QTY', 'Estimated Value (Birr)'], header_fmt)
            row_idx += 1
            opening_rows = [
                ['Residence', report.plan_opening_stock_residence_qty, report.plan_opening_stock_residence_value],
                ['Shops', report.plan_opening_stock_shops_qty, report.plan_opening_stock_shops_value],
                ['Total', report.plan_opening_stock_total_qty, report.plan_opening_stock_total_value],
            ]
            for row in opening_rows:
                worksheet.write(row_idx, 0, row[0], cell_fmt)
                worksheet.write(row_idx, 1, row[1], num_fmt)
                worksheet.write(row_idx, 2, row[2], num_fmt)
                row_idx += 1

            worksheet.set_column(0, 0, 30)
            worksheet.set_column(1, 6, 20)

            workbook.close()
            output.seek(0)

            filename = f'sales_report_{report_type}_{date_from}_{date_to}.xlsx'
            return Response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error exporting Excel: {str(e)}", exc_info=True)
            return request.not_found()
    
    @http.route('/sales_plan_report/api/export_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def export_pdf(self, **kwargs):
        """Export report to PDF"""
        try:
            report_type = kwargs.get('report_type')
            wing_id = kwargs.get('wing_id')
            supervisor_id = kwargs.get('supervisor_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            if date_from:
                date_from = fields.Date.from_string(date_from)
            if date_to:
                date_to = fields.Date.from_string(date_to)
            
            report_vals = {
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
            }
            if report_type == 'wing' and wing_id:
                report_vals['wing_id'] = int(wing_id)
            elif report_type == 'supervisor' and supervisor_id:
                report_vals['supervisor_id'] = int(supervisor_id)
            
            report = request.env['sales.report'].create(report_vals)
            
            # Ensure report data is generated
            report._generate_report()
            request.env.cr.commit()  # Commit to ensure data is available
            
            # Generate PDF using weasyprint (primary method)
            pdf_content = None
            try:
                import weasyprint
                from io import BytesIO
                html_content = self._generate_pdf_html(report, report_type, date_from, date_to)
                pdf_file = BytesIO()
                # Use base_url to resolve relative URLs
                weasyprint.HTML(string=html_content, base_url=request.httprequest.host_url).write_pdf(pdf_file)
                pdf_content = pdf_file.getvalue()
                pdf_file.close()
                if pdf_content and len(pdf_content) > 100:  # Check for valid PDF (PDFs start with %PDF)
                    _logger.info(f"PDF generated successfully using weasyprint ({len(pdf_content)} bytes)")
                else:
                    _logger.warning("PDF content is too small or invalid")
                    pdf_content = None
            except ImportError:
                _logger.error("weasyprint not available. Please install: pip install weasyprint")
                # Try to install weasyprint automatically
                try:
                    import subprocess
                    import sys
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint"])
                    _logger.info("weasyprint installed, retrying PDF generation...")
                    # Retry after installation
                    html_content = self._generate_pdf_html(report, report_type, date_from, date_to)
                    pdf_file = BytesIO()
                    weasyprint.HTML(string=html_content, base_url=request.httprequest.host_url).write_pdf(pdf_file)
                    pdf_content = pdf_file.getvalue()
                    pdf_file.close()
                    if pdf_content and len(pdf_content) > 100:
                        _logger.info("PDF generated successfully after weasyprint installation")
                    else:
                        pdf_content = None
                except Exception as install_error:
                    _logger.error(f"Failed to install weasyprint: {str(install_error)}")
                    pdf_content = None
            except Exception as e:
                _logger.error(f"Error with weasyprint: {str(e)}", exc_info=True)
                pdf_content = None
            
            # Fallback: Try Odoo's report system if weasyprint failed
            if not pdf_content:
                try:
                    report_action = request.env.ref('sales_plan_report.action_report_sales_performance', raise_if_not_found=False)
                    if report_action:
                        result = report_action._render_qweb_pdf(report.ids)
                        if result and isinstance(result, tuple) and len(result) >= 1:
                            pdf_content = result[0]
                            if isinstance(pdf_content, bytes) and len(pdf_content) > 100:
                                _logger.info("PDF generated successfully using Odoo's report system")
                            else:
                                pdf_content = None
                except Exception as e:
                    _logger.error(f"Error with Odoo report system: {str(e)}", exc_info=True)
                    pdf_content = None
            
            # Return PDF if generated
            if pdf_content and isinstance(pdf_content, bytes) and len(pdf_content) > 100:
                filename = f'sales_report_{report_type}_{date_from}_{date_to}.pdf'
                return request.make_response(
                    pdf_content,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
            else:
                # Error: Return error message instead of HTML
                error_msg = "PDF generation failed. Please ensure weasyprint is installed: pip install weasyprint"
                _logger.error(error_msg)
                return request.make_response(
                    error_msg.encode('utf-8'),
                    headers=[
                        ('Content-Type', 'text/plain'),
                        ('Content-Disposition', 'inline'),
                    ]
                )
        except Exception as e:
            _logger.error(f"Error exporting PDF: {str(e)}", exc_info=True)
            return request.not_found()
    
    def _generate_pdf_html(self, report, report_type, date_from, date_to):
        """Generate HTML content for PDF"""
        wing_name = report.wing_id.name if report.wing_id else ''
        supervisor_name = report.supervisor_id.name.name if report.supervisor_id and report.supervisor_id.name else ''
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .metric {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Sales Performance Report</h1>
            <div style="margin-bottom: 20px;">
                <p style="margin: 5px 0;"><strong>Report Type:</strong> {report_type.title()}</p>
                {f'<p style="margin: 5px 0;"><strong>Wing:</strong> {wing_name}</p>' if wing_name else ''}
                {f'<p style="margin: 5px 0;"><strong>Supervisor:</strong> {supervisor_name}</p>' if supervisor_name else ''}
                <p style="margin: 5px 0;"><strong>Date Range:</strong> {date_from} to {date_to}</p>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Actual Previous Week</th>
                        <th>Plan</th>
                        <th>Actual</th>
                        <th>Difference (This week - Previous week)</th>
                        <th>Difference (Actual - Plan)</th>
                        <th>% Achievement</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="metric">Prospects (Leads)</td>
                        <td>{report.actual_previous_week_prospects}</td>
                        <td>{report.plan_prospects}</td>
                        <td>{report.actual_prospects}</td>
                        <td>{report.diff_week_prospects}</td>
                        <td>{report.diff_prospects}</td>
                        <td>{report.percent_prospects:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Follow-ups</td>
                        <td>{report.actual_previous_week_follow_ups}</td>
                        <td>{report.plan_follow_ups}</td>
                        <td>{report.actual_follow_ups}</td>
                        <td>{report.diff_week_follow_ups}</td>
                        <td>{report.diff_follow_ups}</td>
                        <td>{report.percent_follow_ups:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Site Visits</td>
                        <td>{report.actual_previous_week_site_visits}</td>
                        <td>{report.plan_site_visits}</td>
                        <td>{report.actual_site_visits}</td>
                        <td>{report.diff_week_site_visits}</td>
                        <td>{report.diff_site_visits}</td>
                        <td>{report.percent_site_visits:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Office Visits</td>
                        <td>{report.actual_previous_week_office_visits}</td>
                        <td>{report.plan_office_visits}</td>
                        <td>{report.actual_office_visits}</td>
                        <td>{report.diff_week_office_visits}</td>
                        <td>{report.diff_office_visits}</td>
                        <td>{report.percent_office_visits:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Total Visits (Site + Office)</td>
                        <td>{report.actual_previous_week_total_visits}</td>
                        <td>{report.plan_total_visits}</td>
                        <td>{report.actual_total_visits}</td>
                        <td>{report.diff_week_total_visits}</td>
                        <td>{report.diff_total_visits}</td>
                        <td>{report.percent_total_visits:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Total unit reservations</td>
                        <td>{report.actual_previous_week_unit_reservations}</td>
                        <td>{report.plan_unit_reservations}</td>
                        <td>{report.actual_unit_reservations}</td>
                        <td>{report.diff_week_unit_reservations}</td>
                        <td>{report.diff_unit_reservations}</td>
                        <td>{report.percent_unit_reservations:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Deals Closed (QTY)</td>
                        <td>{report.actual_previous_week_deals_closed}</td>
                        <td>{report.plan_deals_closed}</td>
                        <td>{report.actual_deals_closed}</td>
                        <td>{report.diff_week_deals_closed}</td>
                        <td>{report.diff_deals_closed}</td>
                        <td>{report.percent_deals_closed:.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Conversion (sales/leads)</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>{report.conversion_rate:.4f}</td>
                    </tr>
                    <tr>
                        <td class="metric">Cash Collected (Birr)</td>
                        <td>{report.actual_previous_week_cash_collected:.2f}</td>
                        <td>{report.plan_cash_collected:.2f}</td>
                        <td>{report.actual_cash_collected:.2f}</td>
                        <td>{report.diff_week_cash_collected:.2f}</td>
                        <td>{report.diff_cash_collected:.2f}</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td class="metric">Total Deal Value (Birr)</td>
                        <td>{report.actual_previous_week_total_deal_value:.2f}</td>
                        <td>{report.plan_total_deal_value:.2f}</td>
                        <td>{report.actual_total_deal_value:.2f}</td>
                        <td>{report.diff_week_total_deal_value:.2f}</td>
                        <td>{report.diff_total_deal_value:.2f}</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td class="metric">IAR (sales/opening stock)</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>{report.iar_rate:.2f}%</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        return html

