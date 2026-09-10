# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
from datetime import datetime
import logging
import xlsxwriter
import io

from odoo.addons.supervisor_sales_report.controllers.report_metrics import ActivityReportMetrics

_logger = logging.getLogger(__name__)


class TeamActivityReportController(http.Controller):

    def _get_user_ids_for_role(self, user, wing_id=None, sales_manager_id=None):
        """Get all user IDs that should be included based on user's role and wing assignment
        Reuse logic from supervisor_sales_report
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
            if sales_manager_id:
                env.cr.execute("""
                    SELECT DISTINCT t.id, t.manager_id
                    FROM property_sales_wing w
                    LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                    LEFT JOIN property_sales_team t ON t.id = wt.team_id
                    WHERE w.id = %s AND t.manager_id = %s AND t.manager_id IS NOT NULL
                """, (wing_id_for_manager, sales_manager_id))
            else:
                env.cr.execute("""
                    SELECT DISTINCT t.id, t.manager_id
                    FROM property_sales_wing w
                    LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                    LEFT JOIN property_sales_team t ON t.id = wt.team_id
                    WHERE w.id = %s AND t.manager_id IS NOT NULL
                """, (wing_id_for_manager,))
            sales_manager_teams = env.cr.fetchall()
            sales_manager_user_ids = [team[1] for team in sales_manager_teams if team[1]]
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
                
                if supervisor_ids:
                    env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall()]
                    user_ids.extend(supervisor_user_ids)
                
                if supervisor_ids:
                    env.cr.execute("""
                        SELECT DISTINCT pm.user_id
                        FROM property_salesperson_mapping pm
                        WHERE pm.supervisor_id IN %s
                    """, (tuple(supervisor_ids),))
                    salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                    user_ids.extend(salesperson_user_ids)
        
        elif is_admin and (team_result or supervisor_result):
            if team_result:
                team_id = team_result[0]
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
                    supervisor_user_ids = [r[0] for r in env.cr.fetchall()]
                    user_ids.extend(supervisor_user_ids)
                
                if supervisor_ids:
                    env.cr.execute("""
                        SELECT DISTINCT pm.user_id
                        FROM property_salesperson_mapping pm
                        WHERE pm.supervisor_id IN %s
                    """, (tuple(supervisor_ids),))
                    salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                    user_ids.extend(salesperson_user_ids)
            elif supervisor_result:
                supervisor_id = supervisor_result[0]
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id
                    FROM property_salesperson_mapping pm
                    WHERE pm.supervisor_id = %s
                """, (supervisor_id,))
                salesperson_user_ids = [r[0] for r in env.cr.fetchall()]
                user_ids.extend(salesperson_user_ids)
        elif is_admin and wing_id:
            # Admin selected a wing - ONLY include users who actually belong to this wing
            # This ensures users without wing assignment (like admins) are NOT included
            if sales_manager_id:
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id as salesperson_id, s.id as supervisor_id, t.manager_id as team_manager_id
                    FROM property_sales_wing w
                    LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                    LEFT JOIN property_sales_team t ON t.id = wt.team_id
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                    WHERE w.id = %s AND t.manager_id = %s
                    AND pm.user_id IS NOT NULL
                """, (wing_id, sales_manager_id))
            else:
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
            team_id = team_result[0]
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
                user_ids.extend(supervisor_user_ids)
            
            if supervisor_ids:
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id
                    FROM property_salesperson_mapping pm
                    WHERE pm.supervisor_id IN %s AND pm.user_id IS NOT NULL
                """, (tuple(supervisor_ids),))
                salesperson_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                user_ids.extend(salesperson_user_ids)
        elif supervisor_result:
            supervisor_id = supervisor_result[0]
            # Include supervisor's own user ID
            env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id = %s", (supervisor_id,))
            supervisor_user_result = env.cr.fetchone()
            if supervisor_user_result and supervisor_user_result[0]:
                user_ids.append(supervisor_user_result[0])
            
            env.cr.execute("""
                SELECT DISTINCT pm.user_id
                FROM property_salesperson_mapping pm
                WHERE pm.supervisor_id = %s AND pm.user_id IS NOT NULL
            """, (supervisor_id,))
            salesperson_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
            user_ids.extend(salesperson_user_ids)
        
        # Include sales manager's own user ID if they're a team manager
        if team_result:
            team_id = team_result[0]
            env.cr.execute("SELECT manager_id FROM property_sales_team WHERE id = %s", (team_id,))
            team_manager_result = env.cr.fetchone()
            if team_manager_result and team_manager_result[0]:
                user_ids.append(team_manager_result[0])
        
        # Filter by sales_manager_id if provided
        if sales_manager_id:
            # Only include users under the specified sales manager
            env.cr.execute("""
                SELECT DISTINCT s.id as supervisor_id
                FROM property_sales_team t
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                WHERE t.manager_id = %s AND s.id IS NOT NULL
            """, (sales_manager_id,))
            supervisor_ids = [r[0] for r in env.cr.fetchall()]
            
            if supervisor_ids:
                env.cr.execute("SELECT name FROM property_sales_supervisor WHERE id IN %s", (tuple(supervisor_ids),))
                supervisor_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                env.cr.execute("""
                    SELECT DISTINCT pm.user_id
                    FROM property_salesperson_mapping pm
                    WHERE pm.supervisor_id IN %s AND pm.user_id IS NOT NULL
                """, (tuple(supervisor_ids),))
                salesperson_user_ids = [r[0] for r in env.cr.fetchall() if r[0]]
                # Only keep users that are under the sales manager or are the sales manager themselves
                filtered_user_ids = [sales_manager_id] + supervisor_user_ids + salesperson_user_ids
                user_ids = [uid for uid in user_ids if uid in filtered_user_ids]
            else:
                # If no supervisors found, only include the sales manager
                user_ids = [uid for uid in user_ids if uid == sales_manager_id]
        
        return list(set(user_ids))

    def _get_team_activity_data(self, date_from=None, date_to=None, wing_id=None, sales_manager_id=None):
        """Get detailed team activity data grouped by Wing Manager, Supervisor, Salesperson"""
        user = request.env.user
        env = request.env
        
        # Get user IDs based on role (same logic as supervisor_sales_report)
        user_ids = self._get_user_ids_for_role(user, wing_id, sales_manager_id)
        
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
            if sales_manager_id:
                # When both wing_id and sales_manager_id are provided, filter by both
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
                    WHERE w.id = %s AND t.manager_id = %s
                    AND pm.user_id IS NOT NULL
                    ORDER BY um_partner.name, us_partner.name, sp_partner.name
                """
                env.cr.execute(query, (wing_id, sales_manager_id))
            else:
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
            if sales_manager_id:
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
                    WHERE t.manager_id = %s
                    AND (pm.user_id IN %s OR su.id IN %s OR t.manager_id IN %s OR w.manager_id IN %s)
                    AND pm.user_id IS NOT NULL
                    ORDER BY um_partner.name, us_partner.name, sp_partner.name
                """
                env.cr.execute(query, (sales_manager_id, user_ids_tuple, user_ids_tuple, user_ids_tuple, user_ids_tuple))
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
        # This includes all supervisors in the hierarchy, not just the logged-in user
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
        if supervisor_result and user.id not in processed_salesperson_ids:
            supervisors_to_add.add(user.id)
        
        # Add each supervisor's own data
        for supervisor_user_id in supervisors_to_add:
            # Get supervisor's ID from property_sales_supervisor
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (supervisor_user_id,))
            supervisor_id_result = env.cr.fetchone()
            if not supervisor_id_result:
                continue
            
            supervisor_id = supervisor_id_result[0]
            
            # Get supervisor's hierarchy info
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
            # Get all team managers for this wing
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
            # Get team manager's hierarchy info
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
        
        # Add sales manager's own data if not already processed (legacy code for non-admin cases)
        missing_user_ids_set = set(missing_user_ids) if missing_user_ids else set()
        if team_result and user.id not in processed_salesperson_ids and user.id not in team_managers_to_add and user.id not in missing_user_ids_set:
            team_id = team_result[0]
            # Get sales manager's hierarchy info
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
                WHERE t.id = %s LIMIT 1
            """, (team_id,))
            team_hierarchy = env.cr.dictfetchone()
            
            if team_hierarchy:
                sales_manager_metrics = report_metrics.metric_for(metrics_by_user, user.id)
                
                # Get first supervisor for grouping (or use empty)
                env.cr.execute("""
                    SELECT s.id, us_partner.name as supervisor_name
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    LEFT JOIN res_users su ON su.id = s.name
                    LEFT JOIN res_partner us_partner ON us_partner.id = su.partner_id
                    WHERE t.id = %s AND s.id IS NOT NULL LIMIT 1
                """, (team_id,))
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
                
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (user.id,))
                sales_manager_name_result = env.cr.fetchone()
                sales_manager_name = sales_manager_name_result[0] if sales_manager_name_result else user.name
                
                grouped_data[group_key]['salespersons'].append({
                    'salesperson': sales_manager_name or '',
                    'prospect': sales_manager_metrics['prospect'],
                    'follow_up': sales_manager_metrics['follow_up'],
                    'reservation': sales_manager_metrics['reservation'],
                    'sold': sales_manager_metrics['sold'],
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

    def _filter_data_by_search(self, data, search_text):
        """Filter data by search text (supervisor and salesperson names)"""
        if not search_text or not search_text.strip():
            return data
        
        search_lower = search_text.lower().strip()
        filtered_data = []
        
        for group in data:
            # Filter salespersons within each group
            filtered_salespersons = []
            for salesperson in group.get('salespersons', []):
                supervisor_name = (group.get('supervisor', '') or '').lower()
                salesperson_name = (salesperson.get('salesperson', '') or '').lower()
                if search_lower in supervisor_name or search_lower in salesperson_name:
                    filtered_salespersons.append(salesperson)
            
            # Only include group if it has matching salespersons
            if filtered_salespersons:
                filtered_data.append({
                    'wing': group.get('wing', ''),
                    'wing_manager': group.get('wing_manager', ''),
                    'supervisor': group.get('supervisor', ''),
                    'salespersons': filtered_salespersons,
                })
        
        return filtered_data

    def _get_header_info(self, user, data=None, wing_id=None, sales_manager_id=None):
        """Get header info (Wing, Wing Manager, Sales Manager) based on user's role and filters"""
        env = request.env
        header_info = {
            'wing': '',
            'wing_manager': '',
            'sales_manager': '',
        }
        
        # If wing_id filter is provided, use it
        if wing_id:
            env.cr.execute("SELECT id, name, manager_id FROM property_sales_wing WHERE id = %s LIMIT 1", (wing_id,))
            wing_result = env.cr.fetchone()
            if wing_result:
                header_info['wing'] = wing_result[1] or ''
                if wing_result[2]:
                    env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (wing_result[2],))
                    wing_manager_result = env.cr.fetchone()
                    if wing_manager_result:
                        header_info['wing_manager'] = wing_manager_result[0] or ''
        
        # If sales_manager_id filter is provided, use it
        if sales_manager_id:
            env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (sales_manager_id,))
            sales_manager_result = env.cr.fetchone()
            if sales_manager_result:
                header_info['sales_manager'] = sales_manager_result[0] or ''
        
        # If filters not provided, check user's role and get header info
        if not wing_id and not sales_manager_id:
            env.cr.execute("SELECT id, name, manager_id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
            wing_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id, manager_id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
            team_result = env.cr.fetchone()
            
            env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
            supervisor_result = env.cr.fetchone()
            
            if wing_result:
                header_info['wing'] = wing_result[1] or ''
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (user.id,))
                wing_manager_result = env.cr.fetchone()
                if wing_manager_result:
                    header_info['wing_manager'] = wing_manager_result[0] or ''
            elif team_result:
                team_id = team_result[0]
                # Get wing info
                env.cr.execute("""
                    SELECT w.id, w.name, w.manager_id
                    FROM property_sales_wing w
                    LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                    WHERE wt.team_id = %s LIMIT 1
                """, (team_id,))
                wing_info = env.cr.fetchone()
                if wing_info:
                    header_info['wing'] = wing_info[1] or ''
                    if wing_info[2]:
                        env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (wing_info[2],))
                        wing_manager_result = env.cr.fetchone()
                        if wing_manager_result:
                            header_info['wing_manager'] = wing_manager_result[0] or ''
                env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (user.id,))
                sales_manager_result = env.cr.fetchone()
                if sales_manager_result:
                    header_info['sales_manager'] = sales_manager_result[0] or ''
            elif supervisor_result:
                supervisor_id = supervisor_result[0]
                # Get team and wing info
                env.cr.execute("""
                    SELECT t.id, t.manager_id, w.id, w.name, w.manager_id
                    FROM property_sales_supervisor s
                    LEFT JOIN property_team_supervisor_rel ts ON s.id = ts.supervisor_id
                    LEFT JOIN property_sales_team t ON t.id = ts.team_id
                    LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                    LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                    WHERE s.id = %s LIMIT 1
                """, (supervisor_id,))
                hierarchy_info = env.cr.fetchone()
                if hierarchy_info:
                    header_info['wing'] = hierarchy_info[3] or ''
                    if hierarchy_info[4]:
                        env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (hierarchy_info[4],))
                        wing_manager_result = env.cr.fetchone()
                        if wing_manager_result:
                            header_info['wing_manager'] = wing_manager_result[0] or ''
                    if hierarchy_info[1]:
                        env.cr.execute("SELECT name FROM res_partner WHERE id = (SELECT partner_id FROM res_users WHERE id = %s)", (hierarchy_info[1],))
                        sales_manager_result = env.cr.fetchone()
                        if sales_manager_result:
                            header_info['sales_manager'] = sales_manager_result[0] or ''
        
        return header_info

    @http.route('/team_activity_report/api/get_wings', type='json', auth='user')
    def api_get_wings(self, **kwargs):
        """API endpoint to get available wings - Admin only"""
        try:
            user = request.env.user
            env = request.env
            wings = []
            
            # Only allow admin users to access wing selection
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Access denied. Wing selection is only available for administrators.',
                    'wings': [],
                }
            
            # Admin can see all wings
            env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
            results = env.cr.fetchall()
            wings = [{'id': r[0], 'name': r[1]} for r in results]
            
            return {
                'success': True,
                'wings': wings,
            }
        except Exception as e:
            _logger.error(f"Error getting wings: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'wings': [],
            }

    @http.route('/team_activity_report/api/get_sales_managers', type='json', auth='user')
    def api_get_sales_managers(self, wing_id=None, **kwargs):
        """API endpoint to get available sales managers"""
        try:
            user = request.env.user
            env = request.env
            sales_managers = []
            
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            if wing_id:
                if is_admin:
                    env.cr.execute("""
                        SELECT DISTINCT t.manager_id, p.name
                        FROM property_sales_wing w
                        LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                        LEFT JOIN property_sales_team t ON t.id = wt.team_id
                        LEFT JOIN res_users u ON u.id = t.manager_id
                        LEFT JOIN res_partner p ON p.id = u.partner_id
                        WHERE w.id = %s AND t.manager_id IS NOT NULL
                        ORDER BY p.name
                    """, (wing_id,))
                else:
                    # Non-admin: only show sales managers they have access to
                    env.cr.execute("""
                        SELECT DISTINCT t.manager_id, p.name
                        FROM property_sales_wing w
                        LEFT JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                        LEFT JOIN property_sales_team t ON t.id = wt.team_id
                        LEFT JOIN res_users u ON u.id = t.manager_id
                        LEFT JOIN res_partner p ON p.id = u.partner_id
                        WHERE w.id = %s AND t.manager_id IS NOT NULL
                        AND (
                            w.manager_id = %s OR
                            t.manager_id = %s OR
                            EXISTS (
                                SELECT 1 FROM property_team_supervisor_rel ts
                                JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                                WHERE ts.team_id = t.id AND s.name = %s
                            ) OR
                            EXISTS (
                                SELECT 1 FROM property_team_supervisor_rel ts
                                JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                                JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                                WHERE ts.team_id = t.id AND pm.user_id = %s
                            )
                        )
                        ORDER BY p.name
                    """, (wing_id, user.id, user.id, user.id, user.id))
                results = env.cr.fetchall()
                sales_managers = [{'id': r[0], 'name': r[1]} for r in results if r[0] and r[1]]
            else:
                if is_admin:
                    env.cr.execute("""
                        SELECT DISTINCT t.manager_id, p.name
                        FROM property_sales_team t
                        LEFT JOIN res_users u ON u.id = t.manager_id
                        LEFT JOIN res_partner p ON p.id = u.partner_id
                        WHERE t.manager_id IS NOT NULL
                        ORDER BY p.name
                    """)
                else:
                    # Non-admin: only show sales managers they have access to
                    env.cr.execute("""
                        SELECT DISTINCT t.manager_id, p.name
                        FROM property_sales_team t
                        LEFT JOIN res_users u ON u.id = t.manager_id
                        LEFT JOIN res_partner p ON p.id = u.partner_id
                        LEFT JOIN property_wing_team_rel wt ON t.id = wt.team_id
                        LEFT JOIN property_sales_wing w ON w.id = wt.wing_id
                        WHERE t.manager_id IS NOT NULL
                        AND (
                            w.manager_id = %s OR
                            t.manager_id = %s OR
                            EXISTS (
                                SELECT 1 FROM property_team_supervisor_rel ts
                                JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                                WHERE ts.team_id = t.id AND s.name = %s
                            ) OR
                            EXISTS (
                                SELECT 1 FROM property_team_supervisor_rel ts
                                JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                                JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                                WHERE ts.team_id = t.id AND pm.user_id = %s
                            )
                        )
                        ORDER BY p.name
                    """, (user.id, user.id, user.id, user.id))
                results = env.cr.fetchall()
                sales_managers = [{'id': r[0], 'name': r[1]} for r in results if r[0] and r[1]]
            
            return {
                'success': True,
                'sales_managers': sales_managers,
            }
        except Exception as e:
            _logger.error(f"Error getting sales managers: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'sales_managers': [],
            }

    @http.route('/team_activity_report/api/get_data', type='json', auth='user')
    def api_get_data(self, date_from=None, date_to=None, wing_id=None, sales_manager_id=None, **kwargs):
        """API endpoint to get team activity data"""
        try:
            sales_manager_id_int = int(sales_manager_id) if sales_manager_id else None
            wing_id_int = int(wing_id) if wing_id else None
            data = self._get_team_activity_data(date_from, date_to, wing_id_int, sales_manager_id_int)
            header_info = self._get_header_info(request.env.user, data, wing_id_int, sales_manager_id_int)
            
            return {
                'success': True,
                'data': data,
                'header_info': header_info,
            }
        except Exception as e:
            _logger.error(f"Error getting team activity data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    @http.route('/team_activity_report/api/export_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_excel(self, date_from=None, date_to=None, wing_id=None, sales_manager_id=None, search_text=None, **kwargs):
        """Export team activity report to Excel"""
        try:
            sales_manager_id_int = int(sales_manager_id) if sales_manager_id else None
            wing_id_int = int(wing_id) if wing_id else None
            data = self._get_team_activity_data(date_from, date_to, wing_id_int, sales_manager_id_int)
            
            # Filter data by search text if provided
            if search_text:
                data = self._filter_data_by_search(data, search_text)
            
            header_info = self._get_header_info(request.env.user, data, wing_id_int, sales_manager_id_int)
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Team Activity Report')
            
            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
            })
            
            # Info format
            info_format = workbook.add_format({
                'bold': True,
                'align': 'left',
            })
            
            # Data format
            data_format = workbook.add_format({
                'border': 1,
                'align': 'left',
            })
            
            number_format = workbook.add_format({
                'border': 1,
                'align': 'right',
            })
            
            # Get all follow-up activity types
            follow_up_columns = set()
            for group in data:
                if group.get('salespersons'):
                    for salesperson in group['salespersons']:
                        if salesperson.get('follow_up'):
                            for key, value in salesperson['follow_up'].items():
                                if value > 0:
                                    follow_up_columns.add(key)
            follow_up_columns = sorted(list(follow_up_columns))
            
            # Group header format
            group_header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e0e0e0',
                'align': 'left',
                'border': 1,
            })
            
            # Total row format
            total_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e8f4f8',
                'border': 1,
                'align': 'right',
            })
            
            total_label_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e8f4f8',
                'border': 1,
                'align': 'left',
            })
            
            row = 0
            
            # Write header info
            if header_info.get('wing') or header_info.get('wing_manager') or header_info.get('sales_manager') or header_info.get('supervisor'):
                info_parts = []
                if header_info.get('wing'):
                    info_parts.append(f"Wing: {header_info['wing']}")
                if header_info.get('wing_manager'):
                    info_parts.append(f"Wing Manager: {header_info['wing_manager']}")
                if header_info.get('sales_manager'):
                    info_parts.append(f"Sales Manager: {header_info['sales_manager']}")
                if header_info.get('supervisor'):
                    info_parts.append(f"Supervisor: {header_info['supervisor']}")
                if info_parts:
                    worksheet.write(row, 0, " | ".join(info_parts), info_format)
                    row += 1
                    row += 1  # Empty row
            # First row: Main headers
            col = 0
            worksheet.write(row, col, 'Supervisor', header_format)
            col += 1
            worksheet.write(row, col, 'Salesperson', header_format)
            col += 1
            worksheet.write(row, col, 'Prospect', header_format)
            col += 1
            
            # Follow Up header (merged)
            if follow_up_columns:
                worksheet.merge_range(row, col, row, col + len(follow_up_columns), 'Follow Up', header_format)
                col += len(follow_up_columns) + 1
            else:
                worksheet.write(row, col, 'Follow Up', header_format)
                col += 2  # Follow Up + Total
            
            worksheet.write(row, col, 'Reservation', header_format)
            col += 1
            worksheet.write(row, col, 'Sold', header_format)
            row += 1
            
            # Second row: Sub-headers for Follow Up
            col = 0
            worksheet.write(row, col, '', header_format)  # Supervisor
            col += 1
            worksheet.write(row, col, '', header_format)  # Salesperson
            col += 1
            worksheet.write(row, col, '', header_format)  # Prospect
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
                worksheet.write(row, col, 'Total', header_format)
                col += 1
            
            worksheet.write(row, col, '', header_format)  # Reservation
            col += 1
            worksheet.write(row, col, '', header_format)  # Sold
            row += 1
            
            # Initialize totals
            total_prospect = 0
            total_follow_up = {col: 0 for col in follow_up_columns}
            total_follow_up_total = 0
            total_reservation = 0
            total_sold = 0
            
            # Write data grouped by Wing/Wing Manager/Supervisor
            for group in data:
                # Group header row
                group_text = f"Wing: {group.get('wing', '')} | Wing Manager: {group.get('wing_manager', '')} | Supervisor: {group.get('supervisor', '')}"
                worksheet.merge_range(row, 0, row, 1 + len(follow_up_columns) + 3, group_text, group_header_format)
                row += 1
                
                # Salesperson rows
                for salesperson in group.get('salespersons', []):
                    col = 0
                    worksheet.write(row, col, group.get('supervisor', ''), data_format)
                    col += 1
                    worksheet.write(row, col, salesperson.get('salesperson', ''), data_format)
                    col += 1
                    prospect = salesperson.get('prospect', 0)
                    worksheet.write(row, col, prospect, number_format)
                    total_prospect += prospect
                    col += 1
                    
                    # Follow-up activities
                    if follow_up_columns:
                        for activity_type in follow_up_columns:
                            value = salesperson.get('follow_up', {}).get(activity_type, 0) if salesperson.get('follow_up') else 0
                            worksheet.write(row, col, value, number_format)
                            total_follow_up[activity_type] += value
                            col += 1
                        # Total
                        follow_up_total = sum(salesperson.get('follow_up', {}).values()) if salesperson.get('follow_up') else 0
                        worksheet.write(row, col, follow_up_total, number_format)
                        total_follow_up_total += follow_up_total
                        col += 1
                    else:
                        worksheet.write(row, col, 0, number_format)
                        col += 1
                        worksheet.write(row, col, 0, number_format)
                        col += 1
                    
                    reservation = salesperson.get('reservation', 0)
                    worksheet.write(row, col, reservation, number_format)
                    total_reservation += reservation
                    col += 1
                    
                    sold = salesperson.get('sold', 0)
                    worksheet.write(row, col, sold, number_format)
                    total_sold += sold
                    row += 1
            
            # Total row
            col = 0
            worksheet.write(row, col, 'Total', total_label_format)
            col += 1
            worksheet.write(row, col, '', total_format)
            col += 1
            worksheet.write(row, col, total_prospect, total_format)
            col += 1
            
            if follow_up_columns:
                for activity_type in follow_up_columns:
                    worksheet.write(row, col, total_follow_up[activity_type], total_format)
                    col += 1
                worksheet.write(row, col, total_follow_up_total, total_format)
                col += 1
            else:
                worksheet.write(row, col, 0, total_format)
                col += 1
                worksheet.write(row, col, 0, total_format)
                col += 1
            
            worksheet.write(row, col, total_reservation, total_format)
            col += 1
            worksheet.write(row, col, total_sold, total_format)
            
            # Set column widths
            worksheet.set_column(0, 0, 20)  # Supervisor
            worksheet.set_column(1, 1, 20)  # Salesperson
            worksheet.set_column(2, 2, 15)  # Prospect
            worksheet.set_column(3, 3 + len(follow_up_columns) if follow_up_columns else 3, 15)  # Follow-up columns
            worksheet.set_column(4 + len(follow_up_columns) if follow_up_columns else 4, 5 + len(follow_up_columns) if follow_up_columns else 5, 15)  # Reservation, Sold
            
            workbook.close()
            output.seek(0)
            
            filename = f'Team_Activity_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting Excel: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

    @http.route('/team_activity_report/api/export_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_pdf(self, date_from=None, date_to=None, wing_id=None, sales_manager_id=None, search_text=None, **kwargs):
        """Export team activity report to PDF"""
        try:
            sales_manager_id_int = int(sales_manager_id) if sales_manager_id else None
            wing_id_int = int(wing_id) if wing_id else None
            data = self._get_team_activity_data(date_from, date_to, wing_id_int, sales_manager_id_int)
            
            # Filter data by search text if provided
            if search_text:
                data = self._filter_data_by_search(data, search_text)
            
            header_info = self._get_header_info(request.env.user, data, wing_id_int, sales_manager_id_int)
            
            # Get all follow-up activity types
            follow_up_columns = set()
            for group in data:
                if group.get('salespersons'):
                    for salesperson in group['salespersons']:
                        if salesperson.get('follow_up'):
                            for key, value in salesperson['follow_up'].items():
                                if value > 0:
                                    follow_up_columns.add(key)
            follow_up_columns = sorted(list(follow_up_columns))
            
            # Initialize totals
            total_prospect = 0
            total_follow_up = {col: 0 for col in follow_up_columns}
            total_follow_up_total = 0
            total_reservation = 0
            total_sold = 0
            
            # Build header info text
            header_info_parts = []
            if header_info.get('wing'):
                header_info_parts.append(f"Wing: {header_info['wing']}")
            if header_info.get('wing_manager'):
                header_info_parts.append(f"Wing Manager: {header_info['wing_manager']}")
            if header_info.get('sales_manager'):
                header_info_parts.append(f"Sales Manager: {header_info['sales_manager']}")
            if header_info.get('supervisor'):
                header_info_parts.append(f"Supervisor: {header_info['supervisor']}")
            header_info_text = " | ".join(header_info_parts) if header_info_parts else ""
            
            # Build HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Team Activity Report</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }}
                    h1 {{
                        text-align: center;
                        color: #366092;
                    }}
                    .date-range {{
                        text-align: center;
                        margin-bottom: 10px;
                    }}
                    .header-info {{
                        text-align: center;
                        margin-bottom: 20px;
                        padding: 10px;
                        background-color: #f0f0f0;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    th {{
                        background-color: #366092;
                        color: white;
                        padding: 10px;
                        text-align: left;
                        border: 1px solid #ddd;
                    }}
                    td {{
                        padding: 8px;
                        border: 1px solid #ddd;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f2f2f2;
                    }}
                    .number {{
                        text-align: right;
                    }}
                    .group-header {{
                        background-color: #e0e0e0;
                        font-weight: bold;
                        padding: 12px;
                    }}
                    .total-row {{
                        background-color: #e8f4f8;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <h1>Team Activity Report</h1>
                <div class="date-range">
                    <strong>From:</strong> {date_from or 'All'} <strong>To:</strong> {date_to or 'All'}
                </div>
            """
            
            if header_info_text:
                html_content += f"""
                <div class="header-info">
                    {header_info_text}
                </div>
                """
            
            html_content += """
                <table>
                    <thead>
                        <tr>
                            <th>Supervisor</th>
                            <th>Salesperson</th>
                            <th>Prospect</th>
                            <th>Prospect</th>
                            <th colspan="{len(follow_up_columns) + 1 if follow_up_columns else 2}">Follow Up</th>
                            <th>Reservation</th>
                            <th>Sold</th>
                        </tr>
                        <tr>
                            <th></th>
                            <th></th>
                            <th></th>
            """
            
            if follow_up_columns:
                for col in follow_up_columns:
                    html_content += f"<th>{col}</th>"
                html_content += "<th>Total</th>"
            else:
                html_content += "<th></th><th>Total</th>"
            
            html_content += """
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for group in data:
                # Group header row
                group_text = f"Wing: {group.get('wing', '')} | Wing Manager: {group.get('wing_manager', '')} | Supervisor: {group.get('supervisor', '')}"
                html_content += f"""
                        <tr class="group-header">
                            <td colspan="{len(follow_up_columns) + 5 if follow_up_columns else 6}" class="group-header">{group_text}</td>
                        </tr>
                """
                
                # Salesperson rows
                for salesperson in group.get('salespersons', []):
                    prospect = salesperson.get('prospect', 0)
                    total_prospect += prospect
                    
                    html_content += f"""
                        <tr>
                            <td>{group.get('supervisor', '')}</td>
                            <td>{salesperson.get('salesperson', '')}</td>
                            <td class="number">{prospect}</td>
                    """
                    
                    if follow_up_columns:
                        for activity_type in follow_up_columns:
                            value = salesperson.get('follow_up', {}).get(activity_type, 0) if salesperson.get('follow_up') else 0
                            html_content += f'<td class="number">{value}</td>'
                            total_follow_up[activity_type] += value
                        follow_up_total = sum(salesperson.get('follow_up', {}).values()) if salesperson.get('follow_up') else 0
                        html_content += f'<td class="number">{follow_up_total}</td>'
                        total_follow_up_total += follow_up_total
                    else:
                        html_content += '<td class="number">0</td><td class="number">0</td>'
                    
                    reservation = salesperson.get('reservation', 0)
                    total_reservation += reservation
                    sold = salesperson.get('sold', 0)
                    total_sold += sold
                    
                    html_content += f"""
                            <td class="number">{reservation}</td>
                            <td class="number">{sold}</td>
                        </tr>
                    """
            
            # Total row
            html_content += """
                        <tr class="total-row">
                            <td><strong>Total</strong></td>
                            <td></td>
                            <td class="number"><strong>""" + str(total_prospect) + """</strong></td>
            """
            
            if follow_up_columns:
                for activity_type in follow_up_columns:
                    html_content += f'<td class="number"><strong>{total_follow_up[activity_type]}</strong></td>'
                html_content += f'<td class="number"><strong>{total_follow_up_total}</strong></td>'
            else:
                html_content += '<td class="number"><strong>0</strong></td><td class="number"><strong>0</strong></td>'
            
            html_content += f"""
                            <td class="number"><strong>{total_reservation}</strong></td>
                            <td class="number"><strong>{total_sold}</strong></td>
                        </tr>
                    </tbody>
                </table>
                <script>
                    var printExecuted = false;
                    window.onload = function() {{
                        window.print();
                        printExecuted = true;
                    }};
                    
                    // Close after print completes
                    window.onafterprint = function() {{
                        window.close();
                    }};
                    
                    // Handle print media query for better cancel detection
                    if (window.matchMedia) {{
                        var mediaQueryList = window.matchMedia('print');
                        var handlePrintChange = function(mql) {{
                            if (!mql.matches && printExecuted) {{
                                // Print dialog was closed (either printed or cancelled)
                                setTimeout(function() {{
                                    window.close();
                                }}, 500);
                            }}
                        }};
                        mediaQueryList.addListener(handlePrintChange);
                    }}
                    
                    // Fallback: close window after a delay if still open
                    setTimeout(function() {{
                        if (printExecuted) {{
                            window.close();
                        }}
                    }}, 3000);
                </script>
            </body>
            </html>
            """
            
           
            return request.make_response(
                html_content,
                headers=[
                    ('Content-Type', 'text/html'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting PDF: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

