from odoo import http
from odoo.http import request
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


class SalesPlanReportController(http.Controller):

    @http.route('/sales_plan/wing_report', type='http', auth='user', website=False)
    def wing_report_page(self, **kwargs):
        """Render wing report page"""
        return request.render('sales_plan_module.wing_report_template', {})

    @http.route('/sales_plan/supervisor_report', type='http', auth='user', website=False)
    def supervisor_report_page(self, **kwargs):
        """Render supervisor report page"""
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
            supervisor_list = []
            for sup in supervisors:
                display_name = sup.get('name', 'Unknown')
                if isinstance(display_name, tuple):
                    display_name = display_name[1] if len(display_name) > 1 else 'Unknown'
                elif isinstance(display_name, list):
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
            result = request.env['sales.plan'].get_supervisor_report_data(
                int(supervisor_id),
                start_date,
                end_date
            )
            return {'success': True, 'data': result}
        except Exception as e:
            _logger.error(f"Error in supervisor report: {e}")
            return {'success': False, 'error': str(e)}

    def _get_wing_name_for_user(self, user):
        """Get the wing name for a supervisor, sales manager, or wing manager.
        For Sales Managers, returns format: "Team - {WingName}"
        For others, returns just the wing name.
        Same logic as supervisor_sales_report.
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
        
        # Check if user is supervisor
        env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        supervisor_result = env.cr.fetchone()
        
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
        elif supervisor_result:
            # Supervisor - return just wing name
            supervisor_id = supervisor_result[0]
            env.cr.execute("""
                SELECT DISTINCT w.id, w.name
                FROM property_sales_supervisor s
                LEFT JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                LEFT JOIN property_sales_team t ON t.id = ts.team_id
                LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                WHERE s.id = %s AND w.id IS NOT NULL
                LIMIT 1
            """, (supervisor_id,))
            wing_result = env.cr.fetchone()
            if wing_result:
                return wing_result[1]  # Return wing name
        
        return None

    def _get_supervisor_ids_for_role(self, user):
        """
        Get supervisor user IDs based on user's role (same logic as supervisor_sales_report).
        Hierarchy: Wing Manager -> Sales Manager -> Supervisor
        Returns list of supervisor user IDs that the manager can see plans for.
        """
        supervisor_user_ids = []
        env = request.env
        
        # Check if user is admin
        is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
        
        # Check if user is wing manager
        env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
        wing_manager_result = env.cr.fetchone()
        
        # Check if user is team manager (sales manager)
        env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        team_result = env.cr.fetchone()
        
        # Check if user is supervisor
        env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        supervisor_result = env.cr.fetchone()
        
        if wing_manager_result:
            # Wing Manager: Get all supervisors in their wing
            wing_id = wing_manager_result[0]
            _logger.info(f"Wing Manager detected - Wing ID: {wing_id}")
            
            # Get teams in this wing
            env.cr.execute("""
                SELECT DISTINCT t.id
                FROM property_sales_wing w
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                WHERE w.id = %s AND t.id IS NOT NULL
            """, (wing_id,))
            team_ids = [r[0] for r in env.cr.fetchall()]
            
            if team_ids:
                # Get supervisors in these teams
                env.cr.execute("""
                    SELECT DISTINCT s.id
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    WHERE t.id IN %s AND s.id IS NOT NULL
                """, (tuple(team_ids),))
                supervisor_ids = [r[0] for r in env.cr.fetchall()]
                
                if supervisor_ids:
                    # Get supervisor user IDs
                    env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                    _logger.info(f"Found {len(supervisor_user_ids)} supervisors for wing manager: {supervisor_user_ids}")
        
        elif is_admin and (team_result or supervisor_result):
            # Admin who is also a manager/supervisor - use their role
            if team_result:
                # Admin Sales Manager: Get supervisors in their team
                team_id = team_result[0]
                _logger.info(f"Admin Sales Manager detected - Team ID: {team_id}")
                
                env.cr.execute("""
                    SELECT DISTINCT s.id as supervisor_id
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    WHERE t.id = %s AND s.id IS NOT NULL
                """, (team_id,))
                supervisor_ids = [r[0] for r in env.cr.fetchall()]
                
                if supervisor_ids:
                    env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                    _logger.info(f"Found {len(supervisor_user_ids)} supervisors for admin sales manager: {supervisor_user_ids}")
        
        elif team_result:
            # Sales Manager (Team Manager): Get supervisors in their team
            team_id = team_result[0]
            _logger.info(f"Sales Manager detected - Team ID: {team_id}")
            
            env.cr.execute("""
                SELECT DISTINCT s.id as supervisor_id
                FROM property_sales_team t
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                WHERE t.id = %s AND s.id IS NOT NULL
            """, (team_id,))
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
            
            if supervisor_ids:
                env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                _logger.info(f"Found {len(supervisor_user_ids)} supervisors for sales manager: {supervisor_user_ids}")
        
        elif is_admin:
            # Admin (not a manager): Get all supervisors
            env.cr.execute("SELECT name FROM property_sales_supervisor WHERE name IS NOT NULL")
            supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
            _logger.info(f"Admin user - Found {len(supervisor_user_ids)} total supervisors")
        
        # Check if user is CRM Admin (Sales Manager Admin) - they should see all supervisors
        is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
        if is_crm_admin and not wing_manager_result and not team_result:
            # CRM Admin (not a manager): Get all supervisors
            env.cr.execute("SELECT name FROM property_sales_supervisor WHERE name IS NOT NULL")
            supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
            _logger.info(f"CRM Admin user - Found {len(supervisor_user_ids)} total supervisors")
        
        # Supervisors should NOT see this report (they have "Sales Plans" menu instead)
        # So if user is only a supervisor (not a manager), return empty list
        
        final_supervisor_ids = list(set(supervisor_user_ids))
        _logger.info(f"Final supervisor user IDs for {user.name}: {final_supervisor_ids} (count: {len(final_supervisor_ids)})")
        return final_supervisor_ids

    def _get_wing_ids_for_role(self, user):
        """Get wing IDs user can view in Plan Document."""
        env = request.env
        # Admin and CRM Admin can see all wings
        if user.has_group('base.group_system') or user.has_group('base.group_erp_manager') or \
           user.has_group('temer_structure.access_property_crm_admin_group'):
            env.cr.execute("SELECT id FROM property_sales_wing")
            return [r[0] for r in env.cr.fetchall()]

        # Wing manager
        env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s", (user.id,))
        wing_ids = [r[0] for r in env.cr.fetchall()]
        if wing_ids:
            return wing_ids

        # Team manager -> wings linked to team
        env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s", (user.id,))
        team_result = env.cr.fetchone()
        if team_result:
            team_id = team_result[0]
            env.cr.execute("""
                SELECT DISTINCT w.id
                FROM property_sales_team t
                LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                WHERE t.id = %s AND w.id IS NOT NULL
            """, (team_id,))
            return [r[0] for r in env.cr.fetchall()]

        return []

    @http.route('/sales_plan/get_wings_for_plan_document', type='json', auth='user')
    def get_wings_for_plan_document(self, **kwargs):
        """Get wing list for Plan Document filter based on user role."""
        try:
            user = request.env.user
            wing_ids = self._get_wing_ids_for_role(user)
            if wing_ids:
                wings = request.env['property.sales.wing'].search_read(
                    [('id', 'in', wing_ids)], ['id', 'name'], order='name asc'
                )
            else:
                wings = []
            return {'success': True, 'wings': wings}
        except Exception as e:
            _logger.error(f"Error getting wings for plan document: {e}")
            return {'success': False, 'error': str(e)}

    @http.route('/sales_plan/api/plan_document', type='json', auth='user', methods=['POST'], csrf=False)
    def api_plan_document(self, **kwargs):
        """
        API endpoint for Plan Document report.
        Shows supervisors' plans to managers (wing managers, sales managers, and CRM Admin).
        Uses same role detection logic as supervisor_sales_report.
        """
        try:
            params = kwargs.get('params', {}) if isinstance(kwargs.get('params'), dict) else kwargs
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            search_text = params.get('search_text') or kwargs.get('search_text', '').strip()
            wing_id = params.get('wing_id') or kwargs.get('wing_id')
            
            # Convert date strings to date objects
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '':
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '':
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            user = request.env.user
            
            # Check if user is manager, CRM Admin, or system admin (using same logic as supervisor_sales_report)
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_manager_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            
            # Check if user is CRM Admin (Sales Manager Admin)
            is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
            
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            # Only managers, CRM Admin, and system admins can access this API
            is_manager_or_admin = bool(wing_manager_result or team_result or is_crm_admin)
            if not is_manager_or_admin and not is_system_admin:
                return {
                    'success': False,
                    'error': 'Access Denied: Only Sales Manager Admin, Sales Managers, and Wing Managers can view this report.',
                    'data': [],
                    'total': 0
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
            
            # Get supervisor user IDs that this manager can see plans for
            supervisor_user_ids = self._get_supervisor_ids_for_role(user)
            
            if not supervisor_user_ids and not is_system_admin:
                # No supervisors found for this manager
                return {
                    'success': True,
                    'data': [],
                    'total': 0,
                    'role_display': role_display,
                    'selected_wing_name': selected_wing_name,
                }
            
            # Build domain to get plans created by these supervisors
            domain = []
            
            # Filter by supervisor_id (plans must be created by supervisors in manager's hierarchy)
            if supervisor_user_ids:
                # Get supervisor records to match supervisor_id field
                env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name IN %s", (tuple(supervisor_user_ids),))
                supervisor_record_ids = [r[0] for r in env.cr.fetchall()]
                
                _logger.info(f"Found {len(supervisor_record_ids)} supervisor records for user IDs {supervisor_user_ids}")
                
                if supervisor_record_ids:
                    # Filter by supervisor_id OR create_uid (in case supervisor_id is not set)
                    # This ensures we catch plans created by supervisors even if supervisor_id field is empty
                    domain.append('|')
                    domain.append(('supervisor_id', 'in', supervisor_record_ids))
                    domain.append(('create_uid', 'in', supervisor_user_ids))
                else:
                    # No supervisor records found, but try to match by create_uid as fallback
                    _logger.warning(f"No supervisor records found, using create_uid fallback for user IDs: {supervisor_user_ids}")
                    domain.append(('create_uid', 'in', supervisor_user_ids))
            elif is_system_admin:
                # Admin sees all plans (no supervisor filter)
                _logger.info("Admin user - showing all plans")
                pass
            else:
                # No supervisors and not admin, return empty
                _logger.warning(f"No supervisors found for user {user.name} (ID: {user.id})")
                return {
                    'success': True,
                    'data': [],
                    'total': 0,
                    'role_display': role_display,
                    'selected_wing_name': selected_wing_name,
                }
            
            # Add date filters - use overlap logic (show all plans that touch the date range)
            # If user selects Jan 14-16, show all plans where:
            # - plan starts before/on Jan 16 AND plan ends after/on Jan 14
            if date_from_obj and date_to_obj:
                # Plans that overlap with the selected date range
                domain.append(('start_date', '<=', date_to_obj))  # Plan starts before or on end date
                domain.append(('end_date', '>=', date_from_obj))  # Plan ends after or on start date
            elif date_from_obj:
                # Only start date provided - show plans that end on or after this date
                domain.append(('end_date', '>=', date_from_obj))
            elif date_to_obj:
                # Only end date provided - show plans that start on or before this date
                domain.append(('start_date', '<=', date_to_obj))
            
            # Add wing filter (respect user role)
            allowed_wing_ids = self._get_wing_ids_for_role(user)
            if wing_id:
                try:
                    wing_id = int(wing_id)
                except Exception:
                    wing_id = None
            if wing_id:
                if allowed_wing_ids and wing_id in allowed_wing_ids:
                    domain.append(('wing_id', '=', wing_id))
                elif allowed_wing_ids and wing_id not in allowed_wing_ids:
                    domain.append(('wing_id', 'in', allowed_wing_ids))
                else:
                    domain.append(('wing_id', '=', wing_id))
            elif allowed_wing_ids:
                domain.append(('wing_id', 'in', allowed_wing_ids))
            
            _logger.info(f"Searching plans with domain: {domain}")
            # Search plans
            plans = request.env['sales.plan'].search(domain, order='supervisor_id asc, start_date desc, create_date desc')
            _logger.info(f"Found {len(plans)} plans matching the domain")
            
            # Format data
            report_data = []
            for plan in plans:
                # Apply search text filter
                if search_text:
                    search_lower = search_text.lower()
                    plan_name = (plan.name or '').lower()
                    supervisor_name = (plan.supervisor_id.name if plan.supervisor_id else '').lower()
                    wing_name = (plan.wing_id.name if plan.wing_id else '').lower()
                    if search_lower not in plan_name and search_lower not in supervisor_name and search_lower not in wing_name:
                        continue
                
                report_data.append({
                    'id': plan.id,
                    'name': plan.name or '',
                    'plan_type': dict(plan._fields['plan_type'].selection).get(plan.plan_type, plan.plan_type),
                    'start_date': plan.start_date.strftime('%Y-%m-%d') if plan.start_date else '',
                    'end_date': plan.end_date.strftime('%Y-%m-%d') if plan.end_date else '',
                    'supervisor_name': plan.supervisor_id.name if plan.supervisor_id else '',
                    'supervisor_id': plan.supervisor_id.id if plan.supervisor_id else False,
                    'wing_name': plan.wing_id.name if plan.wing_id else '',
                    'created_by': plan.create_uid.name if plan.create_uid else '',
                    'state': dict(plan._fields['state'].selection).get(plan.state, plan.state),
                    'prospect_plan': plan.prospect_plan or 0,
                    'followup_plan': plan.followup_plan or 0,
                    'site_visit_plan': plan.site_visit_plan or 0,
                    'office_visit_plan': plan.office_visit_plan or 0,
                    'total_visit_plan': plan.total_visit_plan or 0,
                    'unit_reservation_plan': plan.unit_reservation_plan or 0,
                    'deals_closed_plan': plan.deals_closed_plan or 0,
                    'cash_collected_plan': plan.cash_collected_plan or 0.0,
                    'total_deal_value_plan': plan.total_deal_value_plan or 0.0,
                    'conversion_plan': plan.conversion_plan or 0.0,
                    'iar_plan': plan.iar_plan or 0.0,
                })
            
            return {
                'success': True,
                'data': report_data,
                'total': len(report_data),
                'role_display': role_display,
                'selected_wing_name': selected_wing_name,
            }
            
        except Exception as e:
            _logger.error(f"Error in plan_document API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0
            }

    @http.route('/sales_plan/api/plan_document_export', type='http', auth='user', methods=['GET'], csrf=False)
    def export_plan_document(self, **kwargs):
        """Export Plan Document to Excel."""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            search_text = (kwargs.get('search_text') or '').strip()
            wing_id = kwargs.get('wing_id')

            date_from_obj = fields.Date.from_string(date_from) if date_from else None
            date_to_obj = fields.Date.from_string(date_to) if date_to else None

            user = request.env.user
            env = request.env

            # Role checks (same as api_plan_document)
            env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_manager_result = env.cr.fetchone()
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')

            is_manager_or_admin = bool(wing_manager_result or team_result or is_crm_admin)
            if not is_manager_or_admin and not is_system_admin:
                return request.not_found()

            # Supervisor scope
            supervisor_user_ids = self._get_supervisor_ids_for_role(user)

            domain = []
            if supervisor_user_ids:
                env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name IN %s", (tuple(supervisor_user_ids),))
                supervisor_record_ids = [r[0] for r in env.cr.fetchall()]
                if supervisor_record_ids:
                    domain.append('|')
                    domain.append(('supervisor_id', 'in', supervisor_record_ids))
                    domain.append(('create_uid', 'in', supervisor_user_ids))
                else:
                    domain.append(('create_uid', 'in', supervisor_user_ids))
            elif not is_system_admin:
                return request.not_found()

            # Date overlap logic
            if date_from_obj and date_to_obj:
                domain.append(('start_date', '<=', date_to_obj))
                domain.append(('end_date', '>=', date_from_obj))
            elif date_from_obj:
                domain.append(('end_date', '>=', date_from_obj))
            elif date_to_obj:
                domain.append(('start_date', '<=', date_to_obj))

            # Wing filter
            allowed_wing_ids = self._get_wing_ids_for_role(user)
            if wing_id:
                try:
                    wing_id = int(wing_id)
                except Exception:
                    wing_id = None
            if wing_id:
                if allowed_wing_ids and wing_id in allowed_wing_ids:
                    domain.append(('wing_id', '=', wing_id))
                elif allowed_wing_ids and wing_id not in allowed_wing_ids:
                    domain.append(('wing_id', 'in', allowed_wing_ids))
                else:
                    domain.append(('wing_id', '=', wing_id))
            elif allowed_wing_ids:
                domain.append(('wing_id', 'in', allowed_wing_ids))

            plans = request.env['sales.plan'].search(domain, order='supervisor_id asc, start_date desc, create_date desc')

            report_data = []
            for plan in plans:
                if search_text:
                    search_lower = search_text.lower()
                    plan_name = (plan.name or '').lower()
                    supervisor_name = (plan.supervisor_id.name if plan.supervisor_id else '').lower()
                    wing_name = (plan.wing_id.name if plan.wing_id else '').lower()
                    if search_lower not in plan_name and search_lower not in supervisor_name and search_lower not in wing_name:
                        continue
                report_data.append([
                    plan.name or '',
                    dict(plan._fields['plan_type'].selection).get(plan.plan_type, plan.plan_type),
                    plan.start_date.strftime('%Y-%m-%d') if plan.start_date else '',
                    plan.end_date.strftime('%Y-%m-%d') if plan.end_date else '',
                    plan.supervisor_id.name if plan.supervisor_id else '',
                    plan.wing_id.name if plan.wing_id else '',
                    plan.create_uid.name if plan.create_uid else '',
                    dict(plan._fields['state'].selection).get(plan.state, plan.state),
                    plan.prospect_plan or 0,
                    plan.followup_plan or 0,
                    plan.site_visit_plan or 0,
                    plan.office_visit_plan or 0,
                    plan.total_visit_plan or 0,
                    plan.unit_reservation_plan or 0,
                    plan.deals_closed_plan or 0,
                    plan.cash_collected_plan or 0.0,
                    plan.total_deal_value_plan or 0.0,
                    plan.conversion_plan or 0.0,
                    plan.iar_plan or 0.0,
                ])

            import io
            import xlsxwriter
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Plan Document')

            header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9E1F2', 'align': 'center'})
            cell_fmt = workbook.add_format({'border': 1})
            num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

            headers = [
                'Plan Name', 'Plan Type', 'From Date', 'To Date', 'Planned By', 'Wing', 'Created By', 'Status',
                'Prospects', 'Follow-ups', 'Site Visits', 'Office Visits', 'Total Visits', 'Unit Reservations',
                'Deals Closed (QTY)', 'Cash Collected (Birr)', 'Total Deal Value (Birr)', 'Conversion (sales/leads)', 'IAR (%)'
            ]
            worksheet.write_row(0, 0, headers, header_fmt)

            row_idx = 1
            for row in report_data:
                worksheet.write(row_idx, 0, row[0], cell_fmt)
                worksheet.write(row_idx, 1, row[1], cell_fmt)
                worksheet.write(row_idx, 2, row[2], cell_fmt)
                worksheet.write(row_idx, 3, row[3], cell_fmt)
                worksheet.write(row_idx, 4, row[4], cell_fmt)
                worksheet.write(row_idx, 5, row[5], cell_fmt)
                worksheet.write(row_idx, 6, row[6], cell_fmt)
                worksheet.write(row_idx, 7, row[7], cell_fmt)
                for col in range(8, 19):
                    worksheet.write(row_idx, col, row[col], num_fmt)
                row_idx += 1

            worksheet.set_column(0, 0, 35)
            worksheet.set_column(1, 7, 18)
            worksheet.set_column(8, 18, 20)

            workbook.close()
            output.seek(0)

            filename = 'plan_document_export.xlsx'
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error exporting plan document: {str(e)}", exc_info=True)
            return request.not_found()
    
    @http.route('/sales_plan/debug_menu_visibility', type='json', auth='user', methods=['POST'], csrf=False)
    def debug_menu_visibility(self, **kwargs):
        """
        Debug endpoint to check menu visibility for current user.
        Call this from browser console or via API to see why menu is/isn't visible.
        """
        try:
            user = request.env.user
            result = request.env['res.users']._check_menu_visibility()
            
            # Also check menu records directly
            menu_root = request.env.ref('sales_plan_module.menu_sales_plan_root', raise_if_not_found=False)
            menu_sales_plan = request.env.ref('sales_plan_module.menu_sales_plan', raise_if_not_found=False)
            menu_plan_document = request.env.ref('sales_plan_module.menu_plan_document', raise_if_not_found=False)
            
            menu_info = {}
            if menu_root:
                menu_info['root_menu'] = {
                    'id': menu_root.id,
                    'name': menu_root.name,
                    'visible': menu_root._is_visible(),
                    'groups': [g.name for g in menu_root.groups_id]
                }
            if menu_sales_plan:
                menu_info['sales_plan_menu'] = {
                    'id': menu_sales_plan.id,
                    'name': menu_sales_plan.name,
                    'visible': menu_sales_plan._is_visible(),
                    'groups': [g.name for g in menu_sales_plan.groups_id]
                }
            if menu_plan_document:
                menu_info['plan_document_menu'] = {
                    'id': menu_plan_document.id,
                    'name': menu_plan_document.name,
                    'visible': menu_plan_document._is_visible(),
                    'groups': [g.name for g in menu_plan_document.groups_id]
                }
            
            result['menu_info'] = menu_info
            
            _logger.info(f"=== DEBUG MENU VISIBILITY RESULT ===")
            _logger.info(f"User: {result['user_name']} (ID: {result['user_id']})")
            _logger.info(f"Menu Visibility: Root={menu_info.get('root_menu', {}).get('visible')}, Sales Plan={menu_info.get('sales_plan_menu', {}).get('visible')}, Plan Document={menu_info.get('plan_document_menu', {}).get('visible')}")
            
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            _logger.error(f"Error in debug_menu_visibility: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }