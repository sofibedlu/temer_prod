# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
from datetime import datetime, time
import logging

from odoo.addons.supervisor_sales_report.controllers.report_metrics import (
    ActivityReportMetrics,
    parse_date_range,
    sum_grouped_metrics,
)

_logger = logging.getLogger(__name__)


class SupervisorSalesReportController(http.Controller):

    def _get_user_ids_for_role(self, user, wing_id=None):
        """Get all user IDs that should be included based on user's role and wing assignment
        Hierarchy: Wing Manager -> Sales Manager -> Supervisor -> Sales Person
        """
        user_ids = [user.id] 
        env = request.env
        
       
        is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
        
       
        env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
        wing_manager_result = env.cr.fetchone()
        
        
        env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        team_result = env.cr.fetchone()
        
     
        env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        supervisor_result = env.cr.fetchone()
        
       
        if wing_manager_result:
            wing_id_for_manager = wing_manager_result[0]
            _logger.info(f"Wing Manager detected - Wing ID: {wing_id_for_manager}")
            
          
            env.cr.execute("""
                SELECT DISTINCT t.id, t.manager_id
                FROM property_sales_wing w
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                WHERE w.id = %s AND t.manager_id IS NOT NULL
            """, (wing_id_for_manager,))
            sales_manager_teams = env.cr.fetchall()
            sales_manager_user_ids = [team[1] for team in sales_manager_teams if team[1]]
            _logger.info(f"Found {len(sales_manager_user_ids)} sales managers: {sales_manager_user_ids}")
            user_ids.extend(sales_manager_user_ids)
            
            
            if sales_manager_teams:
                team_ids = [team[0] for team in sales_manager_teams if team[0]]
                env.cr.execute("""
                    SELECT DISTINCT s.id
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    WHERE t.id IN %s AND s.id IS NOT NULL
                """, (tuple(team_ids),))
                supervisor_ids = [r[0] for r in env.cr.fetchall()]
                _logger.info(f"Found {len(supervisor_ids)} supervisors: {supervisor_ids}")
                
                
                if supervisor_ids:
                    env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall()]
                    _logger.info(f"Supervisor user IDs: {supervisor_user_ids}")
                    user_ids.extend(supervisor_user_ids)
                
              
                if supervisor_ids:
                    env.cr.execute("""
                        SELECT DISTINCT pm.user_id
                        FROM property_salesperson_mapping pm
                        WHERE pm.supervisor_id IN %s
                    """, (tuple(supervisor_ids),))
                    salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                    _logger.info(f"Found {len(salesperson_user_ids)} salespersons: {salesperson_user_ids}")
                    user_ids.extend(salesperson_user_ids)
        
        
        elif is_admin and (team_result or supervisor_result):
          
            if team_result:
              
              
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
                _logger.info(f"Found {len(supervisor_ids)} supervisors under team {team_id}: {supervisor_ids}")
                
              
                if supervisor_ids:
                    env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall()]
                    _logger.info(f"Supervisor user IDs: {supervisor_user_ids}")
                    user_ids.extend(supervisor_user_ids)
                
               
                if supervisor_ids:
                    env.cr.execute("""
                        SELECT DISTINCT pm.user_id
                        FROM property_salesperson_mapping pm
                        WHERE pm.supervisor_id IN %s
                    """, (tuple(supervisor_ids),))
                    salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                    _logger.info(f"Found {len(salesperson_user_ids)} salespersons under supervisors: {salesperson_user_ids}")
                    user_ids.extend(salesperson_user_ids)
            elif supervisor_result:
               
                supervisor_id = supervisor_result[0]
                _logger.info(f"Admin Supervisor detected - Supervisor ID: {supervisor_id}")
                
                
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id
                    FROM property_salesperson_mapping pm
                    WHERE pm.supervisor_id = %s
                """, (supervisor_id,))
                salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                _logger.info(f"Found {len(salesperson_user_ids)} salespersons under supervisor {supervisor_id}: {salesperson_user_ids}")
                user_ids.extend(salesperson_user_ids)
        elif is_admin and wing_id:
            # Admin selected a wing - ONLY include users who actually belong to this wing
            # This ensures users without wing assignment (like admins) are NOT included
            env.cr.execute("""
                SELECT DISTINCT pm.user_id as salesperson_id, s.id as supervisor_id, t.manager_id as team_manager_id
                FROM property_sales_wing w
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                WHERE w.id = %s
                AND pm.user_id IS NOT NULL
            """, (wing_id,))
            results = env.cr.dictfetchall()
            
            supervisor_ids = [r['supervisor_id'] for r in results if r['supervisor_id']]
            if supervisor_ids:
                env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                supervisor_user_ids = [r[0] for r in env.cr.fetchall()]
                user_ids.extend(supervisor_user_ids)
           
            salesperson_user_ids = [r['salesperson_id'] for r in results if r['salesperson_id']]
            user_ids.extend(salesperson_user_ids)
            
            # Include team managers (sales managers) for the wing - only those in this wing
            team_manager_ids = [r['team_manager_id'] for r in results if r['team_manager_id']]
            if team_manager_ids:
                user_ids.extend(team_manager_ids)
           
            # Include wing manager of the selected wing
            env.cr.execute("SELECT manager_id FROM property_sales_wing WHERE id = %s", (wing_id,))
            wing_manager_result = env.cr.fetchone()
            if wing_manager_result and wing_manager_result[0]:
                user_ids.append(wing_manager_result[0])
            
            # Remove the logged-in admin user from user_ids if they don't belong to this wing
            # This prevents admins without wing assignment from appearing in wing-specific reports
            if user.id in user_ids:
                # Check if logged-in user actually belongs to this wing
                env.cr.execute("""
                    SELECT 1 FROM property_sales_wing WHERE id = %s AND manager_id = %s
                    UNION
                    SELECT 1 FROM property_sales_team t
                    JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    WHERE wt.wing_id = %s AND t.manager_id = %s
                    UNION
                    SELECT 1 FROM property_sales_supervisor s
                    JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    JOIN property_sales_team t ON t.id = ts.team_id
                    JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    WHERE wt.wing_id = %s AND s.name = %s
                    UNION
                    SELECT 1 FROM property_salesperson_mapping pm
                    JOIN property_sales_supervisor s ON pm.supervisor_id = s.id
                    JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    JOIN property_sales_team t ON t.id = ts.team_id
                    JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    WHERE wt.wing_id = %s AND pm.user_id = %s
                """, (wing_id, user.id, wing_id, user.id, wing_id, user.id, wing_id, user.id))
                if not env.cr.fetchone():
                    # User doesn't belong to this wing, remove them
                    user_ids = [uid for uid in user_ids if uid != user.id]
        elif team_result:
            # Sales Manager (Team Manager) - see supervisors and salespersons under their team
            team_id = team_result[0]
            _logger.info(f"Sales Manager detected - Team ID: {team_id}, User ID: {user.id}")
            
            # Get supervisors under this team
            env.cr.execute("""
                SELECT DISTINCT s.id as supervisor_id
                FROM property_sales_team t
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                WHERE t.id = %s AND s.id IS NOT NULL
            """, (team_id,))
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
            _logger.info(f"Found {len(supervisor_ids)} supervisors under team {team_id}: {supervisor_ids}")
            
            # Get supervisor user IDs
            if supervisor_ids:
                env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                _logger.info(f"Supervisor user IDs: {supervisor_user_ids}")
                user_ids.extend(supervisor_user_ids)
            
            # Get salespersons under these supervisors
            if supervisor_ids:
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id
                    FROM property_salesperson_mapping pm
                    WHERE pm.supervisor_id IN %s AND pm.user_id IS NOT NULL
                """, (tuple(supervisor_ids),))
                salesperson_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                _logger.info(f"Found {len(salesperson_user_ids)} salespersons under supervisors: {salesperson_user_ids}")
                user_ids.extend(salesperson_user_ids)
        elif supervisor_result:
            supervisor_id = supervisor_result[0]
            _logger.info(f"Supervisor detected - Supervisor ID: {supervisor_id}, User ID: {user.id}")
            
            # Note: user.id is already in user_ids (line 17: user_ids = [user.id])
            # So supervisor's own user ID is already included, no need to add again
            
            # Get salespersons under this supervisor
            env.cr.execute("""
                SELECT DISTINCT pm.user_id
                FROM property_salesperson_mapping pm
                WHERE pm.supervisor_id = %s AND pm.user_id IS NOT NULL
            """, (supervisor_id,))
            salesperson_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
            _logger.info(f"Found {len(salesperson_user_ids)} salespersons under supervisor {supervisor_id}: {salesperson_user_ids}")
            user_ids.extend(salesperson_user_ids)
        
        final_user_ids = list(set(user_ids))
        _logger.info(f"Final user IDs for {user.name}: {final_user_ids} (count: {len(final_user_ids)})")
        return final_user_ids

    def _get_sold_reservation_domain(self, user_ids, date_from_obj=None, date_to_obj=None):
        return ActivityReportMetrics(
            request.env,
            date_from_obj,
            date_to_obj,
        ).sold_reservation_domain(user_ids)

    def _count_sold_reservations(self, user_ids, date_from_obj=None, date_to_obj=None):
        metrics = ActivityReportMetrics(request.env, date_from_obj, date_to_obj)
        return sum(
            user_metrics['sold']
            for user_metrics in metrics.for_users(
                user_ids if isinstance(user_ids, list) else [user_ids]
            ).values()
        )
    
    def _get_wing_name_for_user(self, user):
        """Get the wing name for a supervisor, sales manager, or wing manager.
        For Sales Managers, returns format: "Team - {WingName}"
        For others, returns just the wing name.
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

    @http.route('/supervisor_sales_report/api/report_data', type='json', auth='user', methods=['POST'])
    def api_report_data(self, **kwargs):
        """Get report data based on logged-in user's role and date range"""
        try:
            user = request.env.user
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')  # For admin users
            
           
           
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
         
            user_ids = self._get_user_ids_for_role(user, wing_id=int(wing_id) if wing_id else None)
            
           
            _logger.info(f"Supervisor Sales Report - User: {user.name} (ID: {user.id}), User IDs: {user_ids}, Count: {len(user_ids)}")
            
          
          
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result = env.cr.fetchone()
            
            if is_admin:
                if team_result:
                    user_role = 'admin_sales_manager'
                elif supervisor_result:
                    user_role = 'admin_supervisor'
                else:
                    user_role = 'admin'
            else:
                user_role = 'sales_manager' if team_result else ('supervisor' if supervisor_result else 'salesperson')
            
        
        
            date_from_obj = None
            date_to_obj = None
            if date_from:
                date_from_obj = fields.Date.from_string(date_from)
            if date_to:
                date_to_obj = fields.Date.from_string(date_to)
            
           
           
            # Calculate totals from detailed data to ensure consistency with team_activity_report
            # This ensures both reports always show the same counts
            detailed_data = self._get_detailed_report_data(date_from, date_to, int(wing_id) if wing_id else None, None)
            
            totals = sum_grouped_metrics(detailed_data)
            prospect_count = totals['prospect']
            follow_up_data = totals['follow_up']
            reservation_count = totals['reservation']
            sold_count = totals['sold']
            
            _logger.info(f"FINAL COUNTS (from detailed data) - Prospect: {prospect_count}, Reservation: {reservation_count}, Sold: {sold_count}")
            
            available_wings = []
            selected_wing_name = None
            
           
           
            if team_result or supervisor_result:
            
            
                wing_name = self._get_wing_name_for_user(user)
                if wing_name:
                    selected_wing_name = wing_name
                else:
                  
                  
                    selected_wing_name = "Not Assigned"
            elif is_admin and not team_result and not supervisor_result:
              
              
                env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
                for w_id, w_name in env.cr.fetchall():
                    if w_name:
                        available_wings.append({'id': w_id, 'name': w_name})
                      
                      
                        if wing_id and w_id == wing_id:
                            selected_wing_name = w_name
               
               
                if not selected_wing_name and not wing_id:
                    selected_wing_name = "All Wings"
            else:
               
               
                wing_name = self._get_wing_name_for_user(user)
                if wing_name:
                    selected_wing_name = wing_name
                else:
                    selected_wing_name = "Not Assigned"
            
        
        
            role_display = ''
            if user_role == 'supervisor':
                role_display = 'Supervisor'
            elif user_role == 'sales_manager':
                role_display = 'Sales Manager'
            elif user_role == 'admin_supervisor':
                role_display = 'Admin - Supervisor'
            elif user_role == 'admin_sales_manager':
                role_display = 'Admin - Sales Manager'
            elif user_role == 'admin':
                role_display = 'Admin'
            elif user_role == 'salesperson':
                role_display = 'Salesperson'
            else:
                role_display = user_role.title() if user_role else 'User'
            
            response_data = {
                'success': True,
                'data': {
                    'prospect': prospect_count,
                    'follow_up': follow_up_data,
                    'reservation': reservation_count,
                    'sold': sold_count,
                },
                'user_role': user_role,
                'role_display': role_display,
                'is_admin': is_admin,
                'available_wings': available_wings,
                'selected_wing_name': selected_wing_name,
            }
            
       
       
            _logger.info(f"RESPONSE DATA - reservation: {response_data['data']['reservation']}, sold: {response_data['data']['sold']}")
            
            return response_data
            
        except Exception as e:
            _logger.error(f"Error in supervisor_sales_report api_report_data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    @http.route('/supervisor_sales_report/api/export_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_excel(self, **kwargs):
        """Export report to Excel with proper formatting"""
        try:
            import io
            from odoo.http import Response
            
         
         
            try:
                import xlsxwriter
                use_xlsx = True
            except ImportError:
                import csv
                use_xlsx = False
            
            user = request.env.user
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            
         
         
            user_ids = self._get_user_ids_for_role(user, wing_id=int(wing_id) if wing_id else None)
            
          
          
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result = env.cr.fetchone()
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
          
          
            wing_name = self._get_wing_name_for_user(user)
            if not wing_name and wing_id:
           
           
                env.cr.execute("SELECT name FROM property_sales_wing WHERE id = %s", (int(wing_id),))
                wing_result = env.cr.fetchone()
                if wing_result:
                    wing_name = wing_result[0]
            elif not wing_name and is_admin and not team_result and not supervisor_result:
              
              
                wing_name = "All Wings"
            
         
         
            date_from_obj, date_to_obj = parse_date_range(fields, date_from, date_to)
            user_metrics = ActivityReportMetrics(env, date_from_obj, date_to_obj).for_users(user_ids)
            totals = {
                'prospect': sum(metric['prospect'] for metric in user_metrics.values()),
                'follow_up': {},
                'reservation': sum(metric['reservation'] for metric in user_metrics.values()),
                'sold': sum(metric['sold'] for metric in user_metrics.values()),
            }
            for metric in user_metrics.values():
                for activity_type, count in metric['follow_up'].items():
                    totals['follow_up'][activity_type] = totals['follow_up'].get(activity_type, 0) + count

            prospect_count = totals['prospect']
            follow_up_data = totals['follow_up']
            reservation_count = totals['reservation']
            sold_count = totals['sold']
            follow_up_columns = [k for k in follow_up_data.keys() if follow_up_data[k] > 0]
            follow_up_total = sum(follow_up_data.values())
            
        
        
            date_period = ""
            if date_from and date_to:
                try:
                    date_period = f"FROM {date_from_obj.strftime('%B %d, %Y')} TO {date_to_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"FROM {date_from} TO {date_to}"
            elif date_from:
                try:
                    date_period = f"FROM {date_from_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"FROM {date_from}"
            elif date_to:
                try:
                    date_period = f"TO {date_to_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"TO {date_to}"
            else:
                date_period = "FOR ALL PERIODS"
       
       
            if use_xlsx:
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                worksheet = workbook.add_worksheet()
         
         
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'align': 'center',
                    'valign': 'vcenter',
                })
                subtitle_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'align': 'left',
                    'valign': 'vcenter',
                })
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter',
                    'text_wrap': True,
                })
                cell_format = workbook.add_format({
                    'border': 1,
                    'align': 'left',
                    'valign': 'vcenter',
                })
                number_format = workbook.add_format({
                    'border': 1,
                    'align': 'right',
                    'valign': 'vcenter',
                })
                center_format = workbook.add_format({
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter',
                })
                
                row = 0
                
               
               
                num_cols = 1 + len(follow_up_columns) + (1 if follow_up_columns else 0) + 2  # Prospect + Follow Up cols + Total + Reservation + Sold
                max_col = max(9, num_cols - 1) 
                
                
          
          
                title = "SUPERVISOR SALES REPORT"
             
             
                env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
                team_result = env.cr.fetchone()
                env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
                supervisor_result = env.cr.fetchone()
                is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
                
                if supervisor_result:
                    role_display = 'Supervisor'
                elif team_result:
                    role_display = 'Sales Manager'
                elif is_admin:
                    role_display = 'Admin'
                else:
                    role_display = 'User'
                
                if role_display:
                    title += f" - {role_display}"
                if wing_name:
                    title += f" - {wing_name}"
                elif not wing_name and is_admin and not team_result and not supervisor_result:
                    title += " - All Wings"
                worksheet.merge_range(row, 0, row, max_col, title, title_format)
                row += 1
                
              
              
                worksheet.merge_range(row, 0, row, max_col, date_period, subtitle_format)
                row += 2
                
         
         
                col = 0
                worksheet.write(row, col, 'Total Leads', header_format)
                col += 1
                
                if follow_up_columns:
                    
                    
                    follow_up_cols_count = len(follow_up_columns) + 1  
                    
                    worksheet.merge_range(row, col, row, col + follow_up_cols_count - 1, 'Follow Up', header_format)
                    col += follow_up_cols_count
                else:
                    worksheet.write(row, col, 'Follow Up', header_format)
                    col += 1
                
                worksheet.write(row, col, 'Reservation', header_format)
                col += 1
                worksheet.write(row, col, 'Sold', header_format)
                row += 1
                
              
              
                col = 0
                worksheet.write(row, col, '', header_format)  
                
                col += 1
                
                if follow_up_columns:
                  
                  
                    for col_name in follow_up_columns:
                        worksheet.write(row, col, col_name, header_format)
                        col += 1
                    worksheet.write(row, col, 'Total', header_format)
                    col += 1
                else:
                    worksheet.write(row, col, '', header_format) 
                    
                    col += 1
                
                worksheet.write(row, col, '', header_format) 
                
                col += 1
                worksheet.write(row, col, '', header_format) 
                
                row += 1
                
                # Set column widths
                worksheet.set_column(0, 0, 15)  
                
                if follow_up_columns:
                    start_col = 1
                    for i, col_name in enumerate(follow_up_columns):
                        worksheet.set_column(start_col + i, start_col + i, 18)
                    worksheet.set_column(start_col + len(follow_up_columns), start_col + len(follow_up_columns), 18)  # Total
                    last_col = start_col + len(follow_up_columns)
                else:
                    worksheet.set_column(1, 1, 18)  
                    
                    last_col = 1
                worksheet.set_column(last_col + 1, last_col + 1, 15)
                
                worksheet.set_column(last_col + 2, last_col + 2, 15) 
                
                
                
                
                col = 0
                worksheet.write(row, col, prospect_count, number_format)
                col += 1
                
                follow_up_total = 0
                if follow_up_columns:
                    for col_name in follow_up_columns:
                        value = follow_up_data.get(col_name, 0)
                        worksheet.write(row, col, value, number_format)
                        follow_up_total += value
                        col += 1
                    worksheet.write(row, col, follow_up_total, number_format)
                    col += 1
                else:
                    worksheet.write(row, col, 0, number_format)
                    col += 1
                
                worksheet.write(row, col, reservation_count, number_format)
                col += 1
                worksheet.write(row, col, sold_count, number_format)
                
                workbook.close()
                output.seek(0)
                excel_content = output.getvalue()
                output.close()
                
                filename = f'supervisor_sales_report_{date_from or "all"}_{date_to or "all"}'
                if wing_name:
                    filename += f'_{wing_name.replace(" ", "_")}'
                filename += '.xlsx'
                
                response = Response(
                    excel_content,
                    headers=[
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
                return response
            else:
              
              
                import csv
                output = io.StringIO()
                writer = csv.writer(output)
                
               
               
                env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
                team_result_csv = env.cr.fetchone()
                env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
                supervisor_result_csv = env.cr.fetchone()
                is_admin_csv = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
                
                if supervisor_result_csv:
                    role_display_csv = 'Supervisor'
                elif team_result_csv:
                    role_display_csv = 'Sales Manager'
                elif is_admin_csv:
                    role_display_csv = 'Admin'
                else:
                    role_display_csv = 'User'
                
                csv_title = "SUPERVISOR SALES REPORT"
                if role_display_csv:
                    csv_title += f" - {role_display_csv}"
                if wing_name:
                    csv_title += f" - {wing_name}"
                elif not wing_name and is_admin_csv and not team_result_csv and not supervisor_result_csv:
                    csv_title += " - All Wings"
                writer.writerow([csv_title])
                writer.writerow([date_period])
                writer.writerow([])
                
                headers = ['Total Leads']
                if follow_up_columns:
                    headers.extend(follow_up_columns)
                    headers.append('Total Follow Up')
                else:
                    headers.append('Follow Up')
                headers.extend(['Reservation', 'Sold'])
                writer.writerow(headers)
                
                row_data = [prospect_count]
                if follow_up_columns:
                    for col_name in follow_up_columns:
                        row_data.append(follow_up_data.get(col_name, 0))
                    row_data.append(follow_up_total)
                else:
                    row_data.append(0)
                row_data.extend([reservation_count, sold_count])
                writer.writerow(row_data)
                
                output.seek(0)
                csv_content = output.getvalue()
                output.close()
                
                filename = f'supervisor_sales_report_{date_from or "all"}_{date_to or "all"}'
                if wing_name:
                    filename += f'_{wing_name.replace(" ", "_")}'
                filename += '.csv'
                
                response = Response(
                    csv_content.encode('utf-8-sig'),
                    headers=[
                        ('Content-Type', 'text/csv; charset=utf-8-sig'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
                return response
                
        except Exception as e:
            _logger.error(f"Error in supervisor_sales_report export_excel: {str(e)}", exc_info=True)
            return request.make_response(f"Error exporting Excel: {str(e)}", status=500)

    @http.route('/supervisor_sales_report/api/export_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_pdf(self, **kwargs):
        """Export report to PDF"""
        try:
            user = request.env.user
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            
            # Get report data (same as Excel)
            user_ids = self._get_user_ids_for_role(user, wing_id=int(wing_id) if wing_id else None)
            
            env = request.env
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result = env.cr.fetchone()
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
           
           
            wing_name = self._get_wing_name_for_user(user)
            if not wing_name and wing_id:
               
               
                env.cr.execute("SELECT name FROM property_sales_wing WHERE id = %s", (int(wing_id),))
                wing_result = env.cr.fetchone()
                if wing_result:
                    wing_name = wing_result[0]
            elif not wing_name and is_admin and not team_result and not supervisor_result:
          
          
                wing_name = "All Wings"
            
   
   
            date_from_obj, date_to_obj = parse_date_range(fields, date_from, date_to)
            user_metrics = ActivityReportMetrics(env, date_from_obj, date_to_obj).for_users(user_ids)
            totals = {
                'prospect': sum(metric['prospect'] for metric in user_metrics.values()),
                'follow_up': {},
                'reservation': sum(metric['reservation'] for metric in user_metrics.values()),
                'sold': sum(metric['sold'] for metric in user_metrics.values()),
            }
            for metric in user_metrics.values():
                for activity_type, count in metric['follow_up'].items():
                    totals['follow_up'][activity_type] = totals['follow_up'].get(activity_type, 0) + count

            prospect_count = totals['prospect']
            follow_up_data = totals['follow_up']
            reservation_count = totals['reservation']
            sold_count = totals['sold']
            follow_up_columns = [k for k in follow_up_data.keys() if follow_up_data[k] > 0]
            follow_up_total = sum(follow_up_data.values())
            
            # Format date period
            date_period = ""
            if date_from and date_to:
                try:
                    date_period = f"FROM {date_from_obj.strftime('%B %d, %Y')} TO {date_to_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"FROM {date_from} TO {date_to}"
            elif date_from:
                try:
                    date_period = f"FROM {date_from_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"FROM {date_from}"
            elif date_to:
                try:
                    date_period = f"TO {date_to_obj.strftime('%B %d, %Y')}"
                except:
                    date_period = f"TO {date_to}"
            else:
                date_period = "FOR ALL PERIODS"
            
            
            env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result_pdf = env.cr.fetchone()
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result_pdf = env.cr.fetchone()
            is_admin_pdf = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            if supervisor_result_pdf:
                role_display_pdf = 'Supervisor'
            elif team_result_pdf:
                role_display_pdf = 'Sales Manager'
            elif is_admin_pdf:
                role_display_pdf = 'Admin'
            else:
                role_display_pdf = 'User'
            
            
            follow_up_html = ""
            if follow_up_columns:
                
                follow_up_cols_count = len(follow_up_columns) + 1 
                
                follow_up_html = f"<th colspan='{follow_up_cols_count}'>Follow Up</th>"
            else:
                follow_up_html = "<th>Follow Up</th>"
            
            follow_up_subheader_html = ""
            if follow_up_columns:
               
               
                for col_name in follow_up_columns:
                    follow_up_subheader_html += f"<th>{col_name}</th>"
                follow_up_subheader_html += "<th>Total</th>"
            else:
                follow_up_subheader_html = "<th></th>"
            
            follow_up_data_html = ""
            if follow_up_columns:
                for col_name in follow_up_columns:
                    follow_up_data_html += f"<td class='number'>{follow_up_data.get(col_name, 0)}</td>"
                follow_up_data_html += f"<td class='number'>{follow_up_total}</td>"
            else:
                follow_up_data_html = "<td class='number'>0</td>"
            
        
        
            title_parts_pdf = ["SUPERVISOR SALES REPORT"]
            if role_display_pdf:
                title_parts_pdf.append(role_display_pdf)
            if wing_name:
                title_parts_pdf.append(wing_name)
            elif not wing_name and is_admin_pdf and not team_result_pdf and not supervisor_result_pdf:
                title_parts_pdf.append('All Wings')
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @media print {{
                        @page {{ margin: 1cm; }}
                    }}
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ text-align: center; color: #333; font-size: 18px; margin-bottom: 5px; }}
                    h2 {{ text-align: center; color: #666; font-size: 14px; margin-top: 5px; margin-bottom: 10px; }}
                    .date-period {{ text-align: center; color: #666; font-size: 12px; margin-bottom: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #000; padding: 8px; text-align: left; }}
                    th {{ background-color: #D3D3D3; font-weight: bold; text-align: center; }}
                    .number {{ text-align: right; }}
                </style>
                <script>
                    // Automatically trigger print dialog when page loads
                    window.onload = function() {{
                        window.print();
                    }};
                </script>
            </head>
            <body>
                <h1>{' - '.join(title_parts_pdf)}</h1>
                <div class="date-period">{date_period}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Total Leads</th>
                            {follow_up_html}
                            <th>Reservation</th>
                            <th>Sold</th>
                        </tr>
                        <tr>
                            <th></th>
                            {follow_up_subheader_html}
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="number">{prospect_count}</td>
                            {follow_up_data_html}
                            <td class="number">{reservation_count}</td>
                            <td class="number">{sold_count}</td>
                        </tr>
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            return request.make_response(
                html_content,
                headers=[
                    ('Content-Type', 'text/html'),
                    ('Content-Disposition', 'inline; filename="supervisor_sales_report.html"'),
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error in supervisor_sales_report export_pdf: {str(e)}", exc_info=True)
            return request.make_response(f"Error exporting PDF: {str(e)}", status=500)
    
    @http.route('/supervisor_sales_report/api/get_detail_action', type='json', auth='user', methods=['POST'])
    def api_get_detail_action(self, **kwargs):
        """Get action definition to open detail view for a specific count type"""
        try:
            user = request.env.user
            count_type = kwargs.get('count_type')  # 'prospect', 'reservation', 'sold', 'follow_up'
            activity_type = kwargs.get('activity_type')  # For follow_up type
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            
            # Get user IDs based on role (same logic as api_report_data)
            user_ids = self._get_user_ids_for_role(user, wing_id=int(wing_id) if wing_id else None)
            
            # Parse dates
            date_from_obj = None
            date_to_obj = None
            if date_from:
                date_from_obj = fields.Date.from_string(date_from)
            if date_to:
                date_to_obj = fields.Date.from_string(date_to)
            
            # Build domain based on count_type
            domain = [('id', 'in', [])]  # Default to empty domain if no matches found
            
            if count_type == 'prospect':
                domain = [('user_id', 'in', user_ids)]
                if date_from_obj:
                    domain.append(('create_date', '>=', datetime.combine(date_from_obj, time.min)))
                if date_to_obj:
                    domain.append(('create_date', '<=', datetime.combine(date_to_obj, time.max)))
            
            elif count_type == 'reservation':
                if 'temer.lead.stage.history' in request.env:
                    # Use stage_history to get leads that transitioned to reservation
                    stage_history_domain = [('to_stage', '=', 'reservation')]
                    if date_from_obj:
                        stage_history_domain.append(('transition_date', '>=', date_from_obj))
                    if date_to_obj:
                        if isinstance(date_to_obj, fields.Date):
                            date_to_datetime = datetime.combine(date_to_obj, time.max)
                            stage_history_domain.append(('transition_date', '<=', date_to_datetime))
                        else:
                            stage_history_domain.append(('transition_date', '<=', date_to_obj))
                    
                    reservation_history = request.env['temer.lead.stage.history'].sudo().search(stage_history_domain)
                    reservation_lead_ids = list(set(reservation_history.mapped('lead_id.id')))
                    
                    if reservation_lead_ids:
                        domain = [('id', 'in', reservation_lead_ids), ('user_id', 'in', user_ids), ('state', '=', 'reservation')]
                    else:
                        domain = [('id', 'in', [])]  # No matching records
                else:
                    # Fallback
                    domain = [('user_id', 'in', user_ids), ('state', '=', 'reservation')]
                    if date_from_obj:
                        domain.append(('create_date', '>=', date_from_obj))
                    if date_to_obj:
                        domain.append(('create_date', '<=', date_to_obj))
            
            elif count_type == 'sold':
                domain = self._get_sold_reservation_domain(user_ids, date_from_obj, date_to_obj)
            
            elif count_type == 'follow_up' and activity_type:
                # For follow_up, we want to show leads that have follow-up activities of the specific type
                # First get all leads for the users
                user_leads = request.env['temer.lead'].sudo().search([('user_id', 'in', user_ids)])
                user_lead_ids = user_leads.ids
                
                if user_lead_ids and 'temer.lead.followup' in request.env:
                    # Map activity type name back to code
                    activity_type_map = {
                        'Call': 'call',
                        'SMS': 'sms',
                        'Email': 'email',
                        'Office Visit': 'office_visit',
                        'Site Visit': 'site_visit'
                    }
                    activity_type_code = activity_type_map.get(activity_type, activity_type.lower().replace(' ', '_'))
                    
                    followup_domain = [('lead_id', 'in', user_lead_ids), ('activity_type', '=', activity_type_code)]
                    if date_from_obj:
                        followup_domain.append(('activity_date', '>=', date_from_obj))
                    if date_to_obj:
                        if isinstance(date_to_obj, fields.Date):
                            date_to_datetime = datetime.combine(date_to_obj, time.max)
                            followup_domain.append(('activity_date', '<=', date_to_datetime))
                        else:
                            followup_domain.append(('activity_date', '<=', date_to_obj))
                    
                    followup_activities = request.env['temer.lead.followup'].sudo().search(followup_domain)
                    followup_lead_ids = list(set(followup_activities.mapped('lead_id.id')))
                    
                    if followup_lead_ids:
                        domain = [('id', 'in', followup_lead_ids), ('user_id', 'in', user_ids)]
                    else:
                        domain = [('id', 'in', [])]  # No matching records
                else:
                    domain = [('id', 'in', [])]  # No leads or followup model not available
            
            # Ensure domain is always set
            if not domain or domain is None:
                domain = [('id', 'in', [])]
            
            # Build action
            res_model = 'property.reservation' if count_type == 'sold' else 'temer.lead'
            action = {
                'type': 'ir.actions.act_window',
                'name': f'{count_type.title()} Details',
                'res_model': res_model,
                'view_mode': 'tree,form',
                'views': [[False, 'tree'], [False, 'form']],
                'domain': domain,
                'context': {'create': False},
                'target': 'current',
            }
            
            return {'success': True, 'action': action}
            
        except Exception as e:
            _logger.error(f"Error in supervisor_sales_report api_get_detail_action: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_detailed_report_data(self, date_from=None, date_to=None, wing_id=None, sales_manager_id=None):
        """
        Get detailed report data - same logic as team_activity_report to ensure counts match.
        This method returns the same structure as team_activity_report._get_team_activity_data
        
        COUNTING LOGIC EXPLANATION:
        ===========================
        
        1. PROSPECT COUNT:
           - Counts all leads where user_id = salesperson_id AND create_date is within date range
           - This shows how many new leads/prospects were created by this user in the date range
        
        2. RESERVATION COUNT:
           - Uses temer.lead.stage.history to find leads that transitioned to 'reservation' status within date range
           - Then filters: lead must belong to this user (user_id = salesperson_id) AND current state = 'reservation'
           - This shows how many leads transitioned to reservation by this user in the date range
        
        3. SOLD COUNT:
           - Uses temer.lead.stage.history to find leads that transitioned to 'won' status within date range
           - Then filters: lead must belong to this user (user_id = salesperson_id) AND current state = 'won'
           - This shows how many leads were sold (won) by this user in the date range
        
        4. FOLLOW-UP COUNT:
           - Counts activities from temer.lead.followup table
           - Filters: lead_id belongs to this user AND activity_date is within date range
           - Groups by activity type (Call, SMS, Email, Office Visit, Site Visit)
        
        WING FILTERING (Admin Role):
        ============================
        - When admin selects a wing (wing_id provided), ONLY users from that wing are included:
          * Wing Manager of the selected wing
          * Sales Managers (Team Managers) in teams under the selected wing
          * Supervisors in teams under the selected wing
          * Salespersons mapped to supervisors in the selected wing
        - The query filters by WHERE w.id = %s to ensure only the selected wing's users are shown
        """
        # Reuse team_activity_report logic when that module is installed.
        try:
            from odoo.addons.team_activity_report.controllers.team_activity_report_controller import (
                TeamActivityReportController,
            )
            return TeamActivityReportController()._get_team_activity_data(
                date_from, date_to, wing_id, sales_manager_id
            )
        except ImportError as e:
            _logger.warning(
                "team_activity_report not available, using local fallback: %s", e
            )
        except Exception as e:
            _logger.warning(
                "Could not use team_activity_report method, using fallback: %s", e
            )
        
        # Fallback: Use the same logic directly
        user = request.env.user
        env = request.env
        
        # Get user IDs based on role (same logic as supervisor_sales_report)
        user_ids = self._get_user_ids_for_role(user, wing_id=int(wing_id) if wing_id else None)
        
        # Build date filter for activities
        date_from_obj = None
        date_to_obj = None
        if date_from:
            date_from_obj = fields.Date.from_string(date_from)
        if date_to:
            date_to_obj = fields.Date.from_string(date_to)
        
        # Get team hierarchy data - Group by Wing Manager, Supervisor, Salesperson
        if not user_ids:
            return []
        
        user_ids_tuple = tuple(user_ids) if len(user_ids) > 1 else (user_ids[0],) if user_ids else (0,)
        
        if wing_id:
            # When wing_id is provided (admin selected a wing), ONLY show users from that specific wing
            # No need to filter by user_ids because w.id = %s already ensures we only get users from this wing
            query = """
                SELECT DISTINCT
                    w.id as wing_id,
                    w.name as wing_name,
                    w.manager_id as wing_manager_id,
                    um_partner.name as wing_manager_name,
                    s.id as supervisor_id,
                    su.id as supervisor_user_id,
                    us_partner.name as supervisor_name,
                    pm.user_id as salesperson_id,
                    sp_partner.name as salesperson_name
                FROM property_sales_wing w
                LEFT JOIN res_users um ON um.id = w.manager_id
                LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                LEFT JOIN res_users su ON su.id = s.name
                LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                LEFT JOIN res_users sp ON sp.id = pm.user_id
                LEFT JOIN res_partner sp_partner ON sp_partner.id = sp.partner_id
                WHERE w.id = %s
                AND pm.user_id IS NOT NULL
                ORDER BY um_partner.name, us_partner.name, sp_partner.name
            """
            env.cr.execute(query, (wing_id,))
        else:
            query = """
                SELECT DISTINCT
                    w.id as wing_id,
                    w.name as wing_name,
                    w.manager_id as wing_manager_id,
                    um_partner.name as wing_manager_name,
                    s.id as supervisor_id,
                    su.id as supervisor_user_id,
                    us_partner.name as supervisor_name,
                    pm.user_id as salesperson_id,
                    sp_partner.name as salesperson_name
                FROM property_sales_wing w
                LEFT JOIN res_users um ON um.id = w.manager_id
                LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                LEFT JOIN res_users su ON su.id = s.name
                LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                LEFT JOIN res_users sp ON sp.id = pm.user_id
                LEFT JOIN res_partner sp_partner ON sp_partner.id = sp.partner_id
                WHERE (pm.user_id IN %s OR su.id IN %s OR t.manager_id IN %s OR w.manager_id IN %s)
                AND pm.user_id IS NOT NULL
                ORDER BY um_partner.name, us_partner.name, sp_partner.name
            """
            env.cr.execute(query, (user_ids_tuple, user_ids_tuple, user_ids_tuple, user_ids_tuple))
        
        hierarchy_data = env.cr.dictfetchall()
        
        report_metrics = ActivityReportMetrics(env, date_from_obj, date_to_obj)
        metrics_by_user = report_metrics.for_users(user_ids)
        
        # Group data by Wing, Wing Manager, Supervisor
        grouped_data = {}
        for row in hierarchy_data:
            salesperson_id = row['salesperson_id']
            if not salesperson_id:
                continue
            
            wing_name = row['wing_name'] or ''
            wing_manager = row['wing_manager_name'] or ''
            supervisor = row['supervisor_name'] or ''
            
            # Create grouping key
            group_key = (wing_name, wing_manager, supervisor)
            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    'wing': wing_name,
                    'wing_manager': wing_manager,
                    'supervisor': supervisor,
                    'salespersons': []
                }
            
            salesperson_metrics = report_metrics.metric_for(metrics_by_user, salesperson_id)
            
            grouped_data[group_key]['salespersons'].append({
                'salesperson': row['salesperson_name'] or '',
                'prospect': salesperson_metrics['prospect'],
                'follow_up': salesperson_metrics['follow_up'],
                'reservation': salesperson_metrics['reservation'],
                'sold': salesperson_metrics['sold'],
            })
        
        # Track which user IDs are already in the data as salespersons
        processed_salesperson_ids = set()
        supervisor_ids_in_data = set()
        for row in hierarchy_data:
            if row.get('salesperson_id'):
                processed_salesperson_ids.add(row['salesperson_id'])
            if row.get('supervisor_user_id'):
                supervisor_ids_in_data.add(row['supervisor_user_id'])
        
        # Get all supervisors that should have their own counts included
        supervisors_to_add = set()
        
        # Get logged-in user's role info
        env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        supervisor_result = env.cr.fetchone()
        env.cr.execute("SELECT id, manager_id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        team_result = env.cr.fetchone()
        
        # Add all supervisors from the hierarchy who aren't already salespersons
        for supervisor_user_id in supervisor_ids_in_data:
            if supervisor_user_id not in processed_salesperson_ids:
                supervisors_to_add.add(supervisor_user_id)
        
        # Also add logged-in user if they're a supervisor and not already processed
        # But only if they belong to the selected wing (if wing_id is provided)
        if supervisor_result and user.id not in processed_salesperson_ids:
            if wing_id:
                # Check if this supervisor belongs to the selected wing
                env.cr.execute("""
                    SELECT 1 FROM property_sales_supervisor s
                    LEFT JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    LEFT JOIN property_sales_team t ON t.id = ts.team_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    WHERE s.name = %s AND wt.wing_id = %s
                    LIMIT 1
                """, (user.id, wing_id))
                if env.cr.fetchone():
                    supervisors_to_add.add(user.id)
            else:
                supervisors_to_add.add(user.id)
        
        # Add each supervisor's own data
        for supervisor_user_id in supervisors_to_add:
            # Get supervisor's ID from property_sales_supervisor
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (supervisor_user_id,))
            supervisor_id_result = env.cr.fetchone()
            if not supervisor_id_result:
                continue
            
            supervisor_id = supervisor_id_result[0]
            
            # Get supervisor's hierarchy info - filter by wing_id if provided (admin selected wing)
            if wing_id:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name,
                        s.id as supervisor_id,
                        su.id as supervisor_user_id,
                        us_partner.name as supervisor_name
                    FROM property_sales_supervisor s
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    LEFT JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    LEFT JOIN property_sales_team t ON t.id = ts.team_id
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    WHERE s.id = %s AND w.id = %s LIMIT 1
                """, (supervisor_id, wing_id))
            else:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name,
                        s.id as supervisor_id,
                        su.id as supervisor_user_id,
                        us_partner.name as supervisor_name
                    FROM property_sales_supervisor s
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    LEFT JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    LEFT JOIN property_sales_team t ON t.id = ts.team_id
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    WHERE s.id = %s LIMIT 1
                """, (supervisor_id,))
            supervisor_hierarchy = env.cr.dictfetchone()
            
            if supervisor_hierarchy:
                supervisor_metrics = report_metrics.metric_for(metrics_by_user, supervisor_user_id)
                
                # Add to grouped data
                group_key = (
                    supervisor_hierarchy.get('wing_name') or '',
                    supervisor_hierarchy.get('wing_manager_name') or '',
                    supervisor_hierarchy.get('supervisor_name') or ''
                )
                if group_key not in grouped_data:
                    grouped_data[group_key] = {
                        'wing': supervisor_hierarchy.get('wing_name') or '',
                        'wing_manager': supervisor_hierarchy.get('wing_manager_name') or '',
                        'supervisor': supervisor_hierarchy.get('supervisor_name') or '',
                        'salespersons': []
                    }
                
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (supervisor_user_id,))
                supervisor_name_result = env.cr.fetchone()
                supervisor_name = supervisor_name_result[0] if supervisor_name_result else ''
                
                grouped_data[group_key]['salespersons'].append({
                    'salesperson': supervisor_name or '',
                    'prospect': supervisor_metrics['prospect'],
                    'follow_up': supervisor_metrics['follow_up'],
                    'reservation': supervisor_metrics['reservation'],
                    'sold': supervisor_metrics['sold'],
                })
        
        # Add all team managers (sales managers) for the wing if admin and wing_id is set
        team_managers_to_add = set()
        is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
        
        if is_admin and wing_id:
            # Get all team managers for this wing ONLY (admin selected wing filter)
            env.cr.execute("""
                SELECT DISTINCT t.manager_id
                FROM property_sales_wing w
                LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                LEFT JOIN property_sales_team t ON t.id = wt.team_id
                WHERE w.id = %s AND t.manager_id IS NOT NULL
            """, (wing_id,))
            team_manager_results = env.cr.fetchall()
            for tm_result in team_manager_results:
                if tm_result[0] and tm_result[0] not in processed_salesperson_ids:
                    team_managers_to_add.add(tm_result[0])
        elif team_result and user.id not in processed_salesperson_ids:
            # Add logged-in user if they're a team manager
            team_managers_to_add.add(user.id)
        
        # Add each team manager's own data
        for team_manager_user_id in team_managers_to_add:
            # Get team manager's hierarchy info - filter by wing_id if provided (admin selected wing)
            if wing_id:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name
                    FROM property_sales_team t
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    WHERE t.manager_id = %s AND w.id = %s LIMIT 1
                """, (team_manager_user_id, wing_id))
            else:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name
                    FROM property_sales_team t
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    WHERE t.manager_id = %s LIMIT 1
                """, (team_manager_user_id,))
            team_hierarchy = env.cr.dictfetchone()
            
            if team_hierarchy:
                team_manager_metrics = report_metrics.metric_for(metrics_by_user, team_manager_user_id)
                
                # Get first supervisor for grouping (or use empty)
                env.cr.execute("""
                    SELECT s.id, us_partner.name as supervisor_name
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    WHERE t.manager_id = %s AND s.id IS NOT NULL LIMIT 1
                """, (team_manager_user_id,))
                supervisor_info = env.cr.dictfetchone()
                supervisor_name = supervisor_info.get('supervisor_name') if supervisor_info else ''
                
                # Add to grouped data - use first supervisor's group or create new
                group_key = (
                    team_hierarchy.get('wing_name') or '',
                    team_hierarchy.get('wing_manager_name') or '',
                    supervisor_name
                )
                if group_key not in grouped_data:
                    grouped_data[group_key] = {
                        'wing': team_hierarchy.get('wing_name') or '',
                        'wing_manager': team_hierarchy.get('wing_manager_name') or '',
                        'supervisor': supervisor_name,
                        'salespersons': []
                    }
                
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (team_manager_user_id,))
                sales_manager_name_result = env.cr.fetchone()
                sales_manager_name = sales_manager_name_result[0] if sales_manager_name_result else ''
                
                grouped_data[group_key]['salespersons'].append({
                    'salesperson': sales_manager_name or '',
                    'prospect': team_manager_metrics['prospect'],
                    'follow_up': team_manager_metrics['follow_up'],
                    'reservation': team_manager_metrics['reservation'],
                    'sold': team_manager_metrics['sold'],
                })
        
        # Track all processed user IDs (salespersons, supervisors, team managers)
        all_processed_user_ids = processed_salesperson_ids.copy()
        for sup_id in supervisors_to_add:
            all_processed_user_ids.add(sup_id)
        for tm_id in team_managers_to_add:
            all_processed_user_ids.add(tm_id)
        
        # Find any users from user_ids that haven't been processed yet
        missing_user_ids = [uid for uid in user_ids if uid not in all_processed_user_ids]
        
        # Process any missing users (these might be wing managers or other users)
        # IMPORTANT: When wing_id is provided, only process users who actually belong to that wing
        for missing_user_id in missing_user_ids:
            # Get user's hierarchy info to determine their role
            # If wing_id is provided, ensure user belongs to that wing
            if wing_id:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name,
                        s.id as supervisor_id,
                        su.id as supervisor_user_id,
                        us_partner.name as supervisor_name
                    FROM res_users u
                    LEFT JOIN property_sales_wing w ON w.manager_id = u.id AND w.id = %s
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    LEFT JOIN property_sales_team t ON t.manager_id = u.id
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id AND wt.wing_id = %s
                    LEFT JOIN property_sales_supervisor s ON s.name = u.id
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    WHERE u.id = %s
                    AND (
                        w.id = %s OR 
                        (t.id IS NOT NULL AND EXISTS (
                            SELECT 1 FROM property_wing_team_rel wt2 
                            WHERE wt2.team_id = t.id AND wt2.wing_id = %s
                        )) OR
                        (s.id IS NOT NULL AND EXISTS (
                            SELECT 1 FROM property_team_supervisor_rel ts
                            JOIN property_sales_team t2 ON t2.id = ts.team_id
                            JOIN property_wing_team_rel wt3 ON t2.id = wt3.team_id
                            WHERE ts.supervisor_id = s.id AND wt3.wing_id = %s
                        ))
                    )
                    LIMIT 1
                """, (wing_id, wing_id, missing_user_id, wing_id, wing_id, wing_id))
            else:
                env.cr.execute("""
                    SELECT 
                        w.id as wing_id,
                        w.name as wing_name,
                        w.manager_id as wing_manager_id,
                        um_partner.name as wing_manager_name,
                        t.id as team_id,
                        t.manager_id as team_manager_id,
                        tm_partner.name as team_manager_name,
                        s.id as supervisor_id,
                        su.id as supervisor_user_id,
                        us_partner.name as supervisor_name
                    FROM res_users u
                    LEFT JOIN property_sales_wing w ON w.manager_id = u.id
                    LEFT JOIN res_users um ON um.id = w.manager_id
                    LEFT JOIN res_partner um_partner ON um_partner.id = um.partner_id
                    LEFT JOIN property_sales_team t ON t.manager_id = u.id
                    LEFT JOIN res_users tm ON tm.id = t.manager_id
                    LEFT JOIN res_partner tm_partner ON tm_partner.id = tm.partner_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id AND w.id = wt.wing_id
                    LEFT JOIN property_sales_supervisor s ON s.name = u.id
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    WHERE u.id = %s
                    LIMIT 1
                """, (missing_user_id,))
            user_hierarchy = env.cr.dictfetchone()
            
            # Only process if user belongs to the selected wing (if wing_id is provided)
            if user_hierarchy:
                # If wing_id is provided, verify user actually belongs to that wing
                if wing_id:
                    user_wing_id = user_hierarchy.get('wing_id')
                    if not user_wing_id or user_wing_id != wing_id:
                        # User doesn't belong to selected wing, skip them
                        continue
                missing_user_metrics = report_metrics.metric_for(metrics_by_user, missing_user_id)
                
                # Determine grouping - prefer wing from hierarchy, fallback to wing_id parameter
                wing_name = user_hierarchy.get('wing_name') or ''
                wing_manager_name = user_hierarchy.get('wing_manager_name') or ''
                supervisor_name = user_hierarchy.get('supervisor_name') or ''
                
                # If no supervisor name but user is a supervisor, use their name
                if not supervisor_name and user_hierarchy.get('supervisor_id'):
                    env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (missing_user_id,))
                    supervisor_name_result = env.cr.fetchone()
                    supervisor_name = supervisor_name_result[0] if supervisor_name_result else ''
                
                # If no team manager name but user is a team manager, use their name
                if not supervisor_name and user_hierarchy.get('team_manager_id') == missing_user_id:
                    env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (missing_user_id,))
                    tm_name_result = env.cr.fetchone()
                    if tm_name_result:
                        supervisor_name = tm_name_result[0]
                
                # If still no wing info and wing_id is provided, get it
                if not wing_name and wing_id:
                    env.cr.execute("SELECT name FROM property_sales_wing WHERE id = %s", (wing_id,))
                    wing_result = env.cr.fetchone()
                    if wing_result:
                        wing_name = wing_result[0]
                        env.cr.execute("SELECT manager_id FROM property_sales_wing WHERE id = %s", (wing_id,))
                        wm_result = env.cr.fetchone()
                        if wm_result and wm_result[0]:
                            env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (wm_result[0],))
                            wm_name_result = env.cr.fetchone()
                            if wm_name_result:
                                wing_manager_name = wm_name_result[0]
                
                group_key = (wing_name, wing_manager_name, supervisor_name)
                if group_key not in grouped_data:
                    grouped_data[group_key] = {
                        'wing': wing_name,
                        'wing_manager': wing_manager_name,
                        'supervisor': supervisor_name,
                        'salespersons': []
                    }
                
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (missing_user_id,))
                user_name_result = env.cr.fetchone()
                user_name = user_name_result[0] if user_name_result else ''
                
                grouped_data[group_key]['salespersons'].append({
                    'salesperson': user_name or '',
                    'prospect': missing_user_metrics['prospect'],
                    'follow_up': missing_user_metrics['follow_up'],
                    'reservation': missing_user_metrics['reservation'],
                    'sold': missing_user_metrics['sold'],
                })
        
        # Return grouped data structure
        result_data = []
        for group_key, group_data in sorted(grouped_data.items()):
            result_data.append({
                'wing': group_data['wing'],
                'wing_manager': group_data['wing_manager'],
                'supervisor': group_data['supervisor'],
                'salespersons': group_data['salespersons'],
            })
        
        return result_data
    
    @http.route('/supervisor_sales_report/api/get_detailed_data', type='json', auth='user', methods=['POST'])
    def api_get_detailed_data(self, **kwargs):
        """API endpoint to get detailed report data - same as team_activity_report"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            sales_manager_id = kwargs.get('sales_manager_id')
            
            wing_id_int = int(wing_id) if wing_id else None
            sales_manager_id_int = int(sales_manager_id) if sales_manager_id else None
            
            data = self._get_detailed_report_data(date_from, date_to, wing_id_int, sales_manager_id_int)
            
            # Calculate totals from detailed data to ensure consistency
            total_prospect = 0
            total_follow_up = {}
            total_reservation = 0
            total_sold = 0
            
            for group in data:
                for salesperson in group.get('salespersons', []):
                    total_prospect += salesperson.get('prospect', 0)
                    total_reservation += salesperson.get('reservation', 0)
                    total_sold += salesperson.get('sold', 0)
                    
                    # Sum follow-up activities
                    follow_up = salesperson.get('follow_up', {})
                    if isinstance(follow_up, dict):
                        for activity_type, count in follow_up.items():
                            if activity_type not in total_follow_up:
                                total_follow_up[activity_type] = 0
                            total_follow_up[activity_type] += count
            
            return {
                'success': True,
                'data': data,
                'totals': {
                    'prospect': total_prospect,
                    'follow_up': total_follow_up,
                    'reservation': total_reservation,
                    'sold': total_sold,
                },
                'user_count': len(self._get_user_ids_for_role(request.env.user, wing_id_int))
            }
        except Exception as e:
            _logger.error(f"Error in supervisor_sales_report api_get_detailed_data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

