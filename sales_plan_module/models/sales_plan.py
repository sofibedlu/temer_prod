from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
from odoo.exceptions import ValidationError
from psycopg2 import OperationalError

_logger = logging.getLogger(__name__)


class SalesPlan(models.Model):
    _name = 'sales.plan'
    _description = 'Sales Plan'
    _order = 'start_date desc, create_date desc'
    
    @api.model
    def _get_user_wing_ids(self):
        """Get wing IDs for the current user if they are a supervisor, team manager, wing manager, or CRM Admin"""
        user = self.env.user
        wing_ids = []
        
        try:
            # If user is admin/system user, return empty list (will see all)
            if user.has_group('base.group_system'):
                return []
            
            # Check if user is a wing manager (highest priority - they manage the wing directly)
            if 'property.sales.wing' in self.env:
                wings = self.env['property.sales.wing'].search([
                    ('manager_id', '=', user.id)
                ])
                if wings:
                    wing_ids = wings.ids
                    _logger.info(f"=== WING MANAGER: User {user.name} (ID: {user.id}) is wing manager, wing IDs: {wing_ids}")
                    return wing_ids
            
            # Check if user is a team manager (they manage teams that belong to wings)
            if 'property.sales.team' in self.env:
                teams = self.env['property.sales.team'].search([
                    ('manager_id', '=', user.id)
                ])
                if teams:
                    # Get all wings that contain these teams
                    for team in teams:
                        # Find wing that contains this team - use direct SQL for reliability
                        self.env.cr.execute("""
                            SELECT DISTINCT w.id, w.name
                            FROM property_sales_wing w
                            JOIN property_wing_team_rel wtr ON wtr.wing_id = w.id
                            WHERE wtr.team_id = %s
                        """, (team.id,))
                        results = self.env.cr.fetchall()
                        
                        for wing_id, wing_name in results:
                            if wing_id not in wing_ids:
                                wing_ids.append(wing_id)
                                _logger.info(f"=== TEAM MANAGER: User {user.name} (ID: {user.id}) manages team {team.id}, found wing: {wing_name} (ID: {wing_id})")
                    
                    if wing_ids:
                        return wing_ids
            
            # Check if user is a supervisor
            if 'property.sales.supervisor' in self.env:
                supervisor = self.env['property.sales.supervisor'].search([
                    ('name', '=', user.id)
                ], limit=1)
                
                if supervisor and supervisor.sales_team_id:
                    # Get the team's wing - find which wing has this team
                    team = supervisor.sales_team_id
                    _logger.info(f"=== WING LOOKUP: User {user.name} (ID: {user.id}), supervisor ID: {supervisor.id}, team ID: {team.id}")
                    
                    # Find wing that contains this team - use direct SQL for reliability
                    self.env.cr.execute("""
                        SELECT w.id, w.name
                        FROM property_sales_wing w
                        JOIN property_wing_team_rel wtr ON wtr.wing_id = w.id
                        WHERE wtr.team_id = %s
                        LIMIT 1
                    """, (team.id,))
                    result = self.env.cr.fetchone()
                    
                    if result:
                        wing_id, wing_name = result
                        wing_ids.append(wing_id)
                        _logger.info(f"=== WING FOUND: User {user.name} is supervisor, team: {team.id}, wing: {wing_name} (ID: {wing_id})")
                        return wing_ids
                    else:
                        _logger.warning(f"=== NO WING: User {user.name} (ID: {user.id}) is supervisor but no wing found for team {team.id}")
                
        except Exception as e:
            _logger.warning(f"Error getting user wing IDs: {e}")
        
        # If user is not supervisor, team manager, wing manager, or CRM Admin, return empty (will be filtered out)
        _logger.info(f"User {user.name} (ID: {user.id}) is not supervisor, team manager, wing manager, or CRM Admin, no wing access")
        return wing_ids
    
    @api.model
    def _is_salesperson(self):
        """Check if current user is a salesperson"""
        user = self.env.user
        try:
            if 'property.salesperson.mapping' in self.env:
                salesperson = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', user.id)
                ], limit=1)
                return bool(salesperson)
        except Exception as e:
            _logger.warning(f"Error checking if user is salesperson: {e}")
        return False
    
    @api.model
    def _is_supervisor(self):
        """Check if current user is a supervisor"""
        user = self.env.user
        try:
            if 'property.sales.supervisor' in self.env:
                supervisor = self.env['property.sales.supervisor'].search([
                    ('name', '=', user.id)
                ], limit=1)
                return bool(supervisor)
        except Exception as e:
            _logger.warning(f"Error checking if user is supervisor: {e}")
        return False
    
    @api.model
    def _is_manager_or_crm_admin(self):
        """Check if current user is a team manager, wing manager, or CRM Admin (Sales Manager Admin)"""
        user = self.env.user
        try:
            # Check if user is CRM Admin (Sales Manager Admin)
            if user.has_group('temer_structure.access_property_crm_admin_group'):
                return True
            
            # Check if user is wing manager
            if 'property.sales.wing' in self.env:
                wing = self.env['property.sales.wing'].search([
                    ('manager_id', '=', user.id)
                ], limit=1)
                if wing:
                    return True
            
            # Check if user is team manager
            if 'property.sales.team' in self.env:
                team = self.env['property.sales.team'].search([
                    ('manager_id', '=', user.id)
                ], limit=1)
                if team:
                    return True
        except Exception as e:
            _logger.warning(f"Error checking if user is manager: {e}")
        return False
    
    @api.model
    def _get_supervisor_id_for_user(self):
        """Get supervisor ID for current user (if user is supervisor or under a supervisor)"""
        user = self.env.user
        try:
            # Check if user is directly a supervisor
            if 'property.sales.supervisor' in self.env:
                supervisor = self.env['property.sales.supervisor'].search([
                    ('name', '=', user.id)
                ], limit=1)
                if supervisor:
                    return user.id
                
                # Check if user is under a supervisor (salesperson)
                if 'property.salesperson.mapping' in self.env:
                    salesperson = self.env['property.salesperson.mapping'].search([
                        ('user_id', '=', user.id)
                    ], limit=1)
                    if salesperson and salesperson.supervisor_id:
                        return salesperson.supervisor_id.name.id
        except Exception as e:
            _logger.warning(f"Error getting supervisor ID: {e}")
        return None
    
    def _validate_date_overlap(self, plan_start_date, plan_end_date, plan_supervisor_id, exclude_plan_id=False):
        """Validate that the date range doesn't overlap with existing plans for the same supervisor"""
        # Convert string dates to date objects
        if isinstance(plan_start_date, str):
            plan_start_date = fields.Date.from_string(plan_start_date)
        if isinstance(plan_end_date, str):
            plan_end_date = fields.Date.from_string(plan_end_date)
        
        # Ensure supervisor_id is an integer
        if isinstance(plan_supervisor_id, tuple):
            plan_supervisor_id = plan_supervisor_id[0]
        elif isinstance(plan_supervisor_id, list):
            plan_supervisor_id = plan_supervisor_id[0] if plan_supervisor_id else False
        
        if not plan_start_date or not plan_end_date or not plan_supervisor_id:
            _logger.warning(f"Skipping overlap validation - missing required fields: start_date={plan_start_date}, end_date={plan_end_date}, supervisor_id={plan_supervisor_id}")
            return  # Skip validation if required fields are missing
        
        # Search for overlapping plans using sudo() to bypass _search override
        # Overlap logic: Two date ranges overlap if:
        # - new_start <= existing_end AND new_end >= existing_start
        overlap_domain = [
            ('supervisor_id', '=', plan_supervisor_id),
            ('start_date', '<=', plan_end_date),  # Existing plan starts before or on new plan end
            ('end_date', '>=', plan_start_date),  # Existing plan ends after or on new plan start
        ]
        
        if exclude_plan_id:
            overlap_domain.append(('id', '!=', exclude_plan_id))
        
        _logger.info(f"Checking overlap: start={plan_start_date}, end={plan_end_date}, supervisor={plan_supervisor_id}, exclude={exclude_plan_id}, domain={overlap_domain}")
        
        # Use sudo().search_count() to bypass _search override and avoid SQL errors
        overlap_count = self.sudo().search_count(overlap_domain)
        
        _logger.info(f"Found {overlap_count} overlapping plans")
        
        if overlap_count > 0:
            # Get the actual plans for error message (limit to 3 for display)
            overlapping_plans = self.sudo().search(overlap_domain, limit=3, order='start_date desc')
            plan_names = ', '.join([plan.name for plan in overlapping_plans])
            if overlap_count > 3:
                plan_names += f" and {overlap_count - 3} more plan(s)"
            
            raise ValidationError(
                f"❌ Date Overlap Error!\n\n"
                f"The date range you selected ({plan_start_date.strftime('%d %b %Y')} to {plan_end_date.strftime('%d %b %Y')}) "
                f"overlaps with {overlap_count} existing plan(s) for this supervisor:\n\n"
                f"• {plan_names}\n\n"
                f"Please choose a different date range that doesn't overlap with existing plans."
            )
    
    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """Override _search to filter by creator for supervisors and by wing for managers and CRM Admin"""
        user = self.env.user
        
        # Block salespersons completely - return empty domain that matches nothing
        if self._is_salesperson():
            _logger.info(f"User {user.name} (ID: {user.id}) is a salesperson - blocking access")
            domain = [('id', '=', False)]  # Return domain that matches nothing
        
        # If user is admin, don't filter
        elif not user.has_group('base.group_system'):
            # Check if user is team manager, wing manager, or CRM Admin - they can see all plans in their wing
            if self._is_manager_or_crm_admin():
                wing_ids = self._get_user_wing_ids()
                if wing_ids:
                    # Add wing filter to domain - show all plans from user's wing
                    wing_filter = [('wing_id', 'in', wing_ids)]
                    domain = domain + wing_filter
                    _logger.info(f"=== MANAGER FILTERING: Added wing filter {wing_filter}, final domain: {domain}")
                else:
                    # If manager has no wing, show nothing
                    domain = [('id', '=', False)]
                    _logger.info(f"Manager {user.name} has no wing access, showing no plans")
            
            # If user is a supervisor, only show plans they created
            elif self._is_supervisor():
                # Filter by creator (create_uid)
                creator_filter = [('create_uid', '=', user.id)]
                domain = domain + creator_filter
                _logger.info(f"=== SUPERVISOR FILTERING: Added creator filter {creator_filter}, final domain: {domain}")
            
            # If user is a salesperson under a supervisor, show plans created by their supervisor
            else:
                supervisor_id = self._get_supervisor_id_for_user()
                if supervisor_id:
                    # Show plans created by their supervisor
                    supervisor_user = self.env['res.users'].browse(supervisor_id)
                    creator_filter = [('create_uid', '=', supervisor_id)]
                    domain = domain + creator_filter
                    _logger.info(f"=== SALESPERSON FILTERING: Added supervisor creator filter {creator_filter}, final domain: {domain}")
                else:
                    # If no supervisor found, show nothing
                    domain = [('id', '=', False)]
                    _logger.info(f"User {user.name} has no supervisor, showing no plans")
        
        # Call parent _search with modified domain
        result = super(SalesPlan, self)._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
        # Don't call len() on Query object with ORDER BY - it causes SQL GROUP BY errors
        # Logging is disabled to avoid the error, or we could use search_count() but that would call _search again
        # _logger.info(f"=== _SEARCH RESULT: Found plans for user {user.name}")
        return result

    @api.model
    def get_wing_report_data(self, wing_id, start_date, end_date):
        """Get aggregated report data for a wing"""
        try:
            # Convert string dates to date objects
            if isinstance(start_date, str):
                start_date = fields.Date.from_string(start_date)
            if isinstance(end_date, str):
                end_date = fields.Date.from_string(end_date)

            # Get all supervisors in this wing
            supervisors = self.env['property.sales.supervisor'].search([
                ('sales_team_id.wing_id', '=', wing_id)
            ])
            supervisor_ids = supervisors.mapped('name.id')

            if not supervisor_ids:
                return {'error': 'No supervisors found in this wing'}

            # Get all salespersons under these supervisors
            salesperson_mappings = self.env['property.salesperson.mapping'].search([
                ('supervisor_id.name', 'in', supervisor_ids)
            ])
            salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # All user IDs (supervisors + salespersons)
            all_user_ids = list(set(list(supervisor_ids) + salesperson_ids))

            # Get all plans for these supervisors in the date range
            plans = self.search([
                ('supervisor_id', 'in', supervisor_ids),
                ('start_date', '<=', end_date),
                ('end_date', '>=', start_date),
                ('state', '=', 'completed')
            ])

            # Calculate plan totals (sum of all plans)
            plan_data = {
                'prospects': sum(plans.mapped('prospect_plan')),
                'followups': sum(plans.mapped('followup_plan')),
                'site_visits': sum(plans.mapped('site_visit_plan')),
                'office_visits': sum(plans.mapped('office_visit_plan')),
                'total_visits': sum(plans.mapped('total_visit_plan')),
                'unit_reservations': sum(plans.mapped('unit_reservation_plan')),
                'deals_closed': sum(plans.mapped('deals_closed_plan')),
                'cash_collected': sum(plans.mapped('cash_collected_plan')),
                'total_deal_value': sum(plans.mapped('total_deal_value_plan')),
                'conversion': plans and (sum(plans.mapped('conversion_plan')) / len(plans)) or 0,
                'iar': plans and (sum(plans.mapped('iar_plan')) / len(plans)) or 0,
            }

            # Calculate actual metrics
            actual_data = self._get_actual_metrics_for_users(all_user_ids, start_date, end_date)

            # Calculate previous week metrics
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
            previous_data = self._get_actual_metrics_for_users(all_user_ids, prev_start, prev_end)

            # Prepare result
            result = {
                'wing_name': self.env['property.sales.wing'].browse(wing_id).name,
                'period': f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
                'metrics': {}
            }

            # Define all metrics
            metric_fields = [
                ('prospects', 'Prospects (Leads)', 'integer'),
                ('followups', 'Follow-ups', 'integer'),
                ('site_visits', 'Site Visits', 'integer'),
                ('office_visits', 'Office Visits', 'integer'),
                ('total_visits', 'Total Visits (Site + Office)', 'integer'),
                ('unit_reservations', 'Unit Reservations', 'integer'),
                ('deals_closed', 'Deals Closed (QTY)', 'integer'),
                ('cash_collected', 'Cash Collected (Birr)', 'float'),
                ('total_deal_value', 'Total Deal Value (Birr)', 'float'),
                ('conversion', 'Conversion (sales/leads)', 'float'),
                ('iar', 'IAR (%)', 'float'),
            ]

            for field, label, field_type in metric_fields:
                plan_value = plan_data.get(field, 0)
                actual_value = actual_data.get(field, 0)
                previous_value = previous_data.get(field, 0)

                # Calculate difference (skip for conversion and IAR)
                if field in ['conversion', 'iar']:
                    difference = '-'
                else:
                    difference = actual_value - previous_value

                # Calculate percentage
                if field_type == 'float':
                    plan_value = float(f"{plan_value:.2f}")
                    actual_value = float(f"{actual_value:.2f}")
                    previous_value = float(f"{previous_value:.2f}")

                percentage = 0
                if plan_value > 0:
                    percentage = min(100.0, (actual_value / plan_value) * 100)

                result['metrics'][field] = {
                    'label': label,
                    'plan': plan_value,
                    'actual': actual_value,
                    'previous': previous_value,
                    'difference': difference,
                    'percentage': float(f"{percentage:.1f}"),
                    'type': field_type
                }

            return result

        except Exception as e:
            _logger.error(f"Error getting wing report data: {e}")
            return {'error': str(e)}

    @api.model
    def get_supervisor_report_data(self, supervisor_id, start_date, end_date):
        """Get aggregated report data for a supervisor"""
        """Get aggregated report data for a supervisor"""
        try:
            # Convert string dates to date objects
            if isinstance(start_date, str):
                start_date = fields.Date.from_string(start_date)
            if isinstance(end_date, str):
                end_date = fields.Date.from_string(end_date)

            # Get salespersons under this supervisor
            salesperson_mappings = self.env['property.salesperson.mapping'].search([
                ('supervisor_id.name', '=', supervisor_id)
            ])
            salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # All user IDs (supervisor + salespersons)
            all_user_ids = [supervisor_id] + salesperson_ids

            # Get all plans for this supervisor in the date range
            plans = self.search([
                ('supervisor_id', '=', supervisor_id),
                ('start_date', '<=', end_date),
                ('end_date', '>=', start_date),
                ('state', '=', 'completed')
            ])

            # Calculate plan totals (sum of all plans)
            plan_data = {
                'prospects': sum(plans.mapped('prospect_plan')),
                'followups': sum(plans.mapped('followup_plan')),
                'site_visits': sum(plans.mapped('site_visit_plan')),
                'office_visits': sum(plans.mapped('office_visit_plan')),
                'total_visits': sum(plans.mapped('total_visit_plan')),
                'unit_reservations': sum(plans.mapped('unit_reservation_plan')),
                'deals_closed': sum(plans.mapped('deals_closed_plan')),
                'cash_collected': sum(plans.mapped('cash_collected_plan')),
                'total_deal_value': sum(plans.mapped('total_deal_value_plan')),
                'conversion': plans and (sum(plans.mapped('conversion_plan')) / len(plans)) or 0,
                'iar': plans and (sum(plans.mapped('iar_plan')) / len(plans)) or 0,
            }

            # Calculate actual metrics
            actual_data = self._get_actual_metrics_for_users(all_user_ids, start_date, end_date)

            # Calculate previous week metrics
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
            previous_data = self._get_actual_metrics_for_users(all_user_ids, prev_start, prev_end)

            # Get supervisor and wing info
            supervisor = self.env['property.sales.supervisor'].search([
                ('name', '=', supervisor_id)
            ], limit=1)

            supervisor_name = supervisor.name.name if supervisor else "Unknown"
            wing_name = supervisor.sales_team_id.wing_id.name if supervisor and supervisor.sales_team_id else "N/A"

            # Prepare result
            result = {
                'supervisor_name': supervisor_name,
                'wing_name': wing_name,
                'period': f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
                'metrics': {}
            }

            # Define all metrics (same as wing report)
            metric_fields = [
                ('prospects', 'Prospects (Leads)', 'integer'),
                ('followups', 'Follow-ups', 'integer'),
                ('site_visits', 'Site Visits', 'integer'),
                ('office_visits', 'Office Visits', 'integer'),
                ('total_visits', 'Total Visits (Site + Office)', 'integer'),
                ('unit_reservations', 'Unit Reservations', 'integer'),
                ('deals_closed', 'Deals Closed (QTY)', 'integer'),
                ('cash_collected', 'Cash Collected (Birr)', 'float'),
                ('total_deal_value', 'Total Deal Value (Birr)', 'float'),
                ('conversion', 'Conversion (sales/leads)', 'float'),
                ('iar', 'IAR (%)', 'float'),
            ]

            for field, label, field_type in metric_fields:
                plan_value = plan_data.get(field, 0)
                actual_value = actual_data.get(field, 0)
                previous_value = previous_data.get(field, 0)

                # Calculate difference (skip for conversion and IAR)
                if field in ['conversion', 'iar']:
                    difference = '-'
                else:
                    difference = actual_value - previous_value

                # Calculate percentage
                if field_type == 'float':
                    plan_value = float(f"{plan_value:.2f}")
                    actual_value = float(f"{actual_value:.2f}")
                    previous_value = float(f"{previous_value:.2f}")

                percentage = 0
                if plan_value > 0:
                    percentage = min(100.0, (actual_value / plan_value) * 100)

                result['metrics'][field] = {
                    'label': label,
                    'plan': plan_value,
                    'actual': actual_value,
                    'previous': previous_value,
                    'difference': difference,
                    'percentage': float(f"{percentage:.1f}"),
                    'type': field_type
                }

            return result

        except Exception as e:
            _logger.error(f"Error getting supervisor report data: {e}")
            return {'error': str(e)}

    def _get_actual_metrics_for_users(self, user_ids, start_date, end_date):
        """Get actual metrics for a list of users"""
        result = {
            'prospects': 0,
            'followups': 0,
            'site_visits': 0,
            'office_visits': 0,
            'unit_reservations': 0,
            'deals_closed': 0,
            'cash_collected': 0.0,
            'total_deal_value': 0.0,
        }

        if not user_ids:
            return result

        try:
            # Convert dates to datetime for SQL queries
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Get prospects and followups
            query_leads = """
                          SELECT COUNT(CASE \
                                           WHEN state IN ('prospect', 'reservation', 'won', 'new_lead') \
                                               THEN 1 END)                         as prospects, \
                                 COUNT(CASE \
                                           WHEN state NOT IN ('prospect', 'reservation', 'won', 'new_lead') \
                                               THEN 1 END)                         as followups, \
                                 COUNT(CASE WHEN state = 'reservation' THEN 1 END) as reservations
                          FROM temer_lead
                          WHERE create_date >= %s
                            AND create_date <= %s
                            AND user_id IN %s \
                          """
            self.env.cr.execute(query_leads, (start_datetime, end_datetime, tuple(user_ids)))
            lead_data = self.env.cr.fetchone()

            if lead_data:
                result['prospects'] = lead_data[0] or 0
                result['followups'] = lead_data[1] or 0
                # Reservations and deals are fetched from property models below

            # Get site and office visits
            query_visits = """
                           SELECT COUNT(CASE WHEN activity_type = 'site_visit' THEN 1 END)   as site_visits, \
                                  COUNT(CASE WHEN activity_type = 'office_visit' THEN 1 END) as office_visits
                           FROM temer_lead_activity_wizard
                           WHERE create_date >= %s
                             AND create_date <= %s
                             AND lead_id IN (SELECT id FROM temer_lead WHERE user_id IN %s) \
                           """
            self.env.cr.execute(query_visits, (start_datetime, end_datetime, tuple(user_ids)))
            visit_data = self.env.cr.fetchone()

            if visit_data:
                result['site_visits'] = visit_data[0] or 0
                result['office_visits'] = visit_data[1] or 0

            # Get unit reservations (quick + regular)
            reservation_query = """
                SELECT COUNT(DISTINCT pr.id)
                FROM property_reservation pr
                JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                WHERE DATE(pr.create_date) BETWEEN %s AND %s
                  AND pr.status IN ('reserved', 'requested', 'pending_sales')
                  AND prc.reservation_type IN ('quick', 'regular')
                  AND pr.salesperson_ids IN %s
            """
            self.env.cr.execute(reservation_query, (start_date, end_date, tuple(user_ids)))
            reservation_data = self.env.cr.fetchone()
            result['unit_reservations'] = reservation_data[0] if reservation_data and reservation_data[0] else 0

            # Get deals closed (sold qty)
            deal_query = """
                SELECT COUNT(*)
                FROM property_sale ps
                WHERE DATE(ps.create_date) BETWEEN %s AND %s
                  AND ps.state = 'confirm'
                  AND ps.create_uid IN %s
            """
            self.env.cr.execute(deal_query, (start_date, end_date, tuple(user_ids)))
            deal_data = self.env.cr.fetchone()
            result['deals_closed'] = deal_data[0] if deal_data and deal_data[0] else 0

            # Cash collected (approved reservation payments)
            cash_query = """
                SELECT COALESCE(SUM(prp.amount), 0)
                FROM property_reservation_payment prp
                JOIN property_reservation pr ON pr.id = prp.reservation_id
                JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                WHERE prp.payment_status = 'approved'
                  AND DATE(prp.transaction_date) BETWEEN %s AND %s
                  AND pr.status NOT IN ('canceled', 'expired')
                  AND prc.reservation_type IN ('quick', 'regular')
                  AND pr.salesperson_ids IN %s
            """
            self.env.cr.execute(cash_query, (start_date, end_date, tuple(user_ids)))
            cash_data = self.env.cr.fetchone()
            result['cash_collected'] = cash_data[0] if cash_data and cash_data[0] else 0.0

            # Total deal value (sold amount)
            total_value_query = """
                SELECT COALESCE(SUM(COALESCE(ps.sale_price, 0)), 0)
                FROM property_sale ps
                WHERE DATE(ps.create_date) BETWEEN %s AND %s
                  AND ps.state = 'confirm'
                  AND ps.create_uid IN %s
            """
            self.env.cr.execute(total_value_query, (start_date, end_date, tuple(user_ids)))
            total_value_data = self.env.cr.fetchone()
            result['total_deal_value'] = total_value_data[0] if total_value_data and total_value_data[0] else 0.0

            # Note: You'll need to implement cash_collected and total_deal_value based on your data structure

        except Exception as e:
            _logger.error(f"Error getting actual metrics: {e}")

        return result
    # ========== HELPER METHODS ==========
    def _get_default_supervisor(self):
        """Get default supervisor for current user"""
        user = self.env.user
        _logger.info("Getting supervisor for user: %s - %s", user.id, user.name)

        # Check if property.sales.supervisor model exists
        try:
            if 'property.sales.supervisor' in self.env:
                # 1️⃣ Check if user is directly a supervisor
                supervisor = self.env['property.sales.supervisor'].search(
                    [('name', '=', user.id)],
                    limit=1
                )
                if supervisor:
                    _logger.info(f"Found direct supervisor: {supervisor.id}")
                    return supervisor.name.id

                # 2️⃣ Check if user is in salesperson mapping
                if 'property.salesperson.mapping' in self.env:
                    salesperson = self.env['property.salesperson.mapping'].search(
                        [('user_id', '=', user.id)],
                        limit=1
                    )
                    if salesperson and salesperson.supervisor_id:
                        _logger.info(
                            f"Found supervisor through salesperson mapping: {salesperson.supervisor_id.name.id}")
                        return salesperson.supervisor_id.name.id

                # 3️⃣ Check if user is a sales manager with a team
                if 'property.sales.team' in self.env:
                    team = self.env['property.sales.team'].search(
                        [('manager_id', '=', user.id)],
                        limit=1
                    )
                    if team and team.supervisor_ids:
                        if len(team.supervisor_ids) == 1:
                            _logger.info(f"Found supervisor through team: {team.supervisor_ids[0].name.id}")
                            return team.supervisor_ids[0].name.id
                        else:
                            _logger.warning("Multiple supervisors found in team")
                            return None
        except Exception as e:
            _logger.warning(f"Could not find supervisor models: {e}")

        # Fallback: return current user as supervisor
        _logger.info(f"Using current user as supervisor: {user.id}")
        return user.id

    # ========== BASIC FIELDS ==========
    name = fields.Char(string='Plan Name', required=True, default='New Plan', tracking=True)
    plan_type = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom')
    ], string='Plan Type', default='monthly', required=True)

    period_display = fields.Char(string='Period', compute='_compute_period_display', store=True)

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today(), tracking=True)
    end_date = fields.Date(string='End Date', required=True,
                           default=lambda self: fields.Date.today() + timedelta(days=30), tracking=True)

    # Supervisor field
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        default=lambda self: self._get_default_supervisor(),
        required=True,
        ondelete='cascade',
        tracking=True
    )

    # Wing field
    wing_id = fields.Many2one(
        'property.sales.wing',
        string='Wing',
        compute='_compute_wing_id',
        store=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed')
    ], string='Status', default='draft', tracking=True)
    
    # Computed field to check if plan is past due
    is_past_due = fields.Boolean(string='Is Past Due', compute='_compute_is_past_due', store=False)
    
    @api.depends('end_date')
    def _compute_is_past_due(self):
        """Compute if plan end date has passed"""
        today = fields.Date.today()
        for record in self:
            record.is_past_due = record.end_date and record.end_date < today

    # ========== PLAN TARGETS ==========
    prospect_plan = fields.Integer(string='Prospects Plan', default=0)
    followup_plan = fields.Integer(string='Follow-ups Plan', default=0)
    site_visit_plan = fields.Integer(string='Site Visits Plan', default=0)
    office_visit_plan = fields.Integer(string='Office Visits Plan', default=0)
    total_visit_plan = fields.Integer(string='Total Visits Plan', compute='_compute_total_plan', store=True)

    # New metrics for quarterly plans
    unit_reservation_plan = fields.Integer(string='Unit Reservations Plan', default=0)
    deals_closed_plan = fields.Integer(string='Deals Closed Plan (QTY)', default=0)
    cash_collected_plan = fields.Float(string='Cash Collected Plan (Birr)', default=0.0, digits=(12, 2))
    total_deal_value_plan = fields.Float(string='Total Deal Value Plan (Birr)', default=0.0, digits=(12, 2))
    conversion_plan = fields.Float(string='Conversion Plan', default=0.0, digits=(8, 4))
    iar_plan = fields.Float(string='IAR Plan (%)', default=0.0, digits=(5, 2))
    opening_stock_residence_qty_plan = fields.Integer(string='Opening Stock Residence QTY Plan', default=0)
    opening_stock_residence_value_plan = fields.Float(string='Opening Stock Residence Value Plan (Birr)', default=0.0, digits=(12, 2))
    opening_stock_shops_qty_plan = fields.Integer(string='Opening Stock Shops QTY Plan', default=0)
    opening_stock_shops_value_plan = fields.Float(string='Opening Stock Shops Value Plan (Birr)', default=0.0, digits=(12, 2))
    opening_stock_total_qty_plan = fields.Integer(string='Opening Stock Total QTY Plan', compute='_compute_opening_stock_plan_total', store=True)
    opening_stock_total_value_plan = fields.Float(string='Opening Stock Total Value Plan (Birr)', compute='_compute_opening_stock_plan_total', store=True, digits=(12, 2))

    # ========== REMARKS ==========
    prospect_remark = fields.Text(string='Prospects Remark')
    followup_remark = fields.Text(string='Follow-ups Remark')
    site_visit_remark = fields.Text(string='Site Visits Remark')
    office_visit_remark = fields.Text(string='Office Visits Remark')
    total_visit_remark = fields.Text(string='Total Visits Remark')
    unit_reservation_remark = fields.Text(string='Unit Reservations Remark')
    deals_closed_remark = fields.Text(string='Deals Closed Remark')
    cash_collected_remark = fields.Text(string='Cash Collected Remark')
    total_deal_value_remark = fields.Text(string='Total Deal Value Remark')
    conversion_remark = fields.Text(string='Conversion Remark')
    iar_remark = fields.Text(string='IAR Remark')

    # ========== ACTUAL METRICS ==========
    actual_prospects = fields.Integer(string='Actual Prospects', compute='_compute_actual_metrics', store=True)
    actual_followups = fields.Integer(string='Actual Follow-ups', compute='_compute_actual_metrics', store=True)
    actual_site_visits = fields.Integer(string='Actual Site Visits', compute='_compute_actual_metrics', store=True)
    actual_office_visits = fields.Integer(string='Actual Office Visits', compute='_compute_actual_metrics', store=True)
    actual_total_visits = fields.Integer(string='Actual Total Visits', compute='_compute_actual_metrics', store=True)

    # New actual metrics
    actual_unit_reservations = fields.Integer(string='Actual Unit Reservations', compute='_compute_actual_metrics',
                                              store=True)
    actual_deals_closed = fields.Integer(string='Actual Deals Closed (QTY)', compute='_compute_actual_metrics',
                                         store=True)
    actual_cash_collected = fields.Float(string='Actual Cash Collected (Birr)', compute='_compute_actual_metrics',
                                         store=True, digits=(12, 2))
    actual_total_deal_value = fields.Float(string='Actual Total Deal Value (Birr)', compute='_compute_actual_metrics',
                                           store=True, digits=(12, 2))
    actual_conversion = fields.Float(string='Actual Conversion', compute='_compute_actual_metrics', store=True,
                                     digits=(8, 4))
    actual_iar = fields.Float(string='Actual IAR (%)', compute='_compute_actual_metrics', store=True, digits=(5, 2))
    actual_opening_stock_residence_qty = fields.Integer(string='Actual Opening Stock Residence QTY', compute='_compute_actual_metrics', store=True)
    actual_opening_stock_residence_value = fields.Float(string='Actual Opening Stock Residence Value (Birr)', compute='_compute_actual_metrics', store=True, digits=(12, 2))
    actual_opening_stock_shops_qty = fields.Integer(string='Actual Opening Stock Shops QTY', compute='_compute_actual_metrics', store=True)
    actual_opening_stock_shops_value = fields.Float(string='Actual Opening Stock Shops Value (Birr)', compute='_compute_actual_metrics', store=True, digits=(12, 2))
    actual_opening_stock_total_qty = fields.Integer(string='Actual Opening Stock Total QTY', compute='_compute_actual_metrics', store=True)
    actual_opening_stock_total_value = fields.Float(string='Actual Opening Stock Total Value (Birr)', compute='_compute_actual_metrics', store=True, digits=(12, 2))

    # ========== PREVIOUS WEEK METRICS ==========
    previous_prospects = fields.Integer(string='Previous Week Prospects', compute='_compute_previous_metrics',
                                        store=True)
    previous_followups = fields.Integer(string='Previous Week Follow-ups', compute='_compute_previous_metrics',
                                        store=True)
    previous_site_visits = fields.Integer(string='Previous Week Site Visits', compute='_compute_previous_metrics',
                                          store=True)
    previous_office_visits = fields.Integer(string='Previous Week Office Visits', compute='_compute_previous_metrics',
                                            store=True)
    previous_total_visits = fields.Integer(string='Previous Week Total Visits', compute='_compute_previous_metrics',
                                           store=True)

    # New previous metrics
    previous_unit_reservations = fields.Integer(string='Previous Unit Reservations',
                                                compute='_compute_previous_metrics', store=True)
    previous_deals_closed = fields.Integer(string='Previous Deals Closed', compute='_compute_previous_metrics',
                                           store=True)
    previous_cash_collected = fields.Float(string='Previous Cash Collected', compute='_compute_previous_metrics',
                                           store=True, digits=(12, 2))
    previous_total_deal_value = fields.Float(string='Previous Total Deal Value', compute='_compute_previous_metrics',
                                             store=True, digits=(12, 2))

    # ========== DIFFERENCES ==========
    prospect_difference = fields.Integer(string='Prospects Difference', compute='_compute_differences', store=True)
    followup_difference = fields.Integer(string='Follow-ups Difference', compute='_compute_differences', store=True)
    site_visit_difference = fields.Integer(string='Site Visits Difference', compute='_compute_differences', store=True)
    office_visit_difference = fields.Integer(string='Office Visits Difference', compute='_compute_differences',
                                             store=True)
    total_visit_difference = fields.Integer(string='Total Visits Difference', compute='_compute_differences',
                                            store=True)

    # New difference fields
    unit_reservation_difference = fields.Integer(string='Unit Reservations Difference', compute='_compute_differences',
                                                 store=True)
    deals_closed_difference = fields.Integer(string='Deals Closed Difference', compute='_compute_differences',
                                             store=True)
    cash_collected_difference = fields.Float(string='Cash Collected Difference', compute='_compute_differences',
                                             store=True, digits=(12, 2))
    total_deal_value_difference = fields.Float(string='Total Deal Value Difference', compute='_compute_differences',
                                               store=True, digits=(12, 2))

    # ========== PERCENTAGE COMPLETION ==========
    prospect_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    followup_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    site_visit_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    office_visit_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    total_visit_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))

    # New percentage fields
    unit_reservation_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    deals_closed_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    cash_collected_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    total_deal_value_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    conversion_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))
    iar_percentage = fields.Float(string='%', compute='_compute_percentages', store=True, digits=(12, 2))

    # ========== COMPUTED METHODS ==========
    def _generate_plan_name(self):
        """Generate plan name: from_date to to_date for wing_name by supervisor_name"""
        if self.start_date and self.end_date:
            # Format dates: "01 Dec 2025 to 31 Dec 2025"
            start_str = self.start_date.strftime('%d %b %Y')
            end_str = self.end_date.strftime('%d %b %Y')
            date_part = f"{start_str} to {end_str}"
            
            # Get wing name
            wing_name = self.wing_id.name if self.wing_id else "No Wing"
            
            # Get supervisor name
            supervisor_name = self.supervisor_id.name if self.supervisor_id else "No Supervisor"
            
            # Generate name: "01 Dec 2025 to 31 Dec 2025 for Wing Name by Supervisor Name"
            return f"{date_part} for {wing_name} by {supervisor_name}"
        return "New Plan"
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate plan name, validate date overlap, and prevent managers from creating"""
        user = self.env.user

        # Admin users must NOT create plans even if they are supervisors
        if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
            raise ValidationError(
                "❌ Access Denied!\n\n"
                "System Admin users cannot create sales plans. "
                "Only Supervisors assigned to a Wing can create plans."
            )

        # Prevent Sales Manager Admin, Sales Managers, and Wing Managers from creating plans
        is_manager_or_admin = False
        if user.has_group('temer_structure.access_property_crm_admin_group'):
            is_manager_or_admin = True
        if not is_manager_or_admin and 'property.sales.team' in self.env:
            teams = self.env['property.sales.team'].search([('manager_id', '=', user.id)], limit=1)
            if teams:
                is_manager_or_admin = True
        if not is_manager_or_admin and 'property.sales.wing' in self.env:
            wings = self.env['property.sales.wing'].search([('manager_id', '=', user.id)], limit=1)
            if wings:
                is_manager_or_admin = True
        if is_manager_or_admin:
            raise ValidationError(
                "❌ Access Denied!\n\n"
                "Sales Manager Admin, Sales Managers, and Wing Managers cannot create sales plans. "
                "Only Supervisors assigned to a Wing can create plans."
            )

        # Only supervisors linked to a wing can create plans
        supervisor_record = self.env['property.sales.supervisor'].search([('name', '=', user.id)], limit=1)
        if not supervisor_record:
            raise ValidationError(
                "❌ Access Denied!\n\n"
                "Only Supervisors assigned to a Wing can create plans."
            )
        team = self.env['property.sales.team'].search([('supervisor_ids', 'in', supervisor_record.id)], limit=1)
        if not team or not team.wing_id:
            raise ValidationError(
                "❌ Access Denied!\n\n"
                "Supervisor must be assigned to a Wing before creating a plan."
            )
        
        for vals in vals_list:
            # Validate dates are not in the past (allow today)
            today = fields.Date.today()
            start_date = vals.get('start_date')
            end_date = vals.get('end_date')
            
            if isinstance(start_date, str) and start_date:
                start_date = fields.Date.from_string(start_date)
            if isinstance(end_date, str) and end_date:
                end_date = fields.Date.from_string(end_date)
            
            if start_date and start_date < today:
                raise ValidationError(
                    f"❌ Invalid Start Date!\n\n"
                    f"You cannot create a plan with a start date ({start_date.strftime('%d %b %Y')}) in the past. "
                    f"Please select today ({today.strftime('%d %b %Y')}) or a future date."
                )
            
            if end_date and end_date < today:
                raise ValidationError(
                    f"❌ Invalid End Date!\n\n"
                    f"You cannot create a plan with an end date ({end_date.strftime('%d %b %Y')}) in the past. "
                    f"Please select today ({today.strftime('%d %b %Y')}) or a future date."
                )
            
            if start_date and end_date and start_date > end_date:
                raise ValidationError(
                    f"❌ Invalid Date Range!\n\n"
                    f"The start date ({start_date.strftime('%d %b %Y')}) cannot be after the end date ({end_date.strftime('%d %b %Y')}). "
                    f"Please correct the date range."
                )
            
            # Auto-generate name if not provided or is default
            if not vals.get('name') or vals.get('name') == 'New Plan':
                # Create a temporary record to generate name
                temp_record = self.new(vals)
                vals['name'] = temp_record._generate_plan_name()
            
            # Validate date overlap (use already converted date objects)
            supervisor_id = vals.get('supervisor_id')
            
            # If supervisor_id is not provided, try to get it from default
            if not supervisor_id:
                # Get default supervisor for current user
                temp_record = self.new(vals)
                if hasattr(temp_record, '_get_default_supervisor'):
                    supervisor_id = temp_record._get_default_supervisor()
            
            if start_date and end_date:
                # Ensure supervisor_id is an integer (not a tuple from Many2one)
                if isinstance(supervisor_id, tuple):
                    supervisor_id = supervisor_id[0]
                elif isinstance(supervisor_id, list):
                    supervisor_id = supervisor_id[0] if supervisor_id else False
                
                # If still no supervisor_id, we can't validate overlap - skip
                if supervisor_id:
                    _logger.info(f"Validating overlap for create: start={start_date}, end={end_date}, supervisor={supervisor_id}")
                    self._validate_date_overlap(start_date, end_date, supervisor_id, exclude_plan_id=False)
                else:
                    _logger.warning(f"Cannot validate overlap - supervisor_id is missing. start_date={start_date}, end_date={end_date}")
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to auto-update plan name, validate date overlap, and check edit permissions"""
        today = fields.Date.today()
        
        # Check if user can edit (plan date must not be due/past)
        # Only check for past due if trying to edit important fields
        editable_fields = ['start_date', 'end_date', 'supervisor_id', 'prospect_plan', 'followup_plan', 
                          'site_visit_plan', 'office_visit_plan', 'prospect_remark', 'followup_remark',
                          'site_visit_remark', 'office_visit_remark', 'total_visit_remark']
        
        if any(key in vals for key in editable_fields):
            for record in self:
                # Get current dates
                current_start_date = record.start_date
                current_end_date = record.end_date
                
                # Get new dates (convert strings to date objects if needed)
                new_start_date = vals.get('start_date')
                new_end_date = vals.get('end_date')
                
                if isinstance(new_start_date, str):
                    new_start_date = fields.Date.from_string(new_start_date) if new_start_date else None
                if isinstance(new_end_date, str):
                    new_end_date = fields.Date.from_string(new_end_date) if new_end_date else None
                
                # Use new dates if provided, otherwise use current dates
                start_date_to_check = new_start_date if new_start_date else current_start_date
                end_date_to_check = new_end_date if new_end_date else current_end_date
                
                # Check if plan date is due (past) - only for date/plan value changes
                changing_dates = 'start_date' in vals or 'end_date' in vals
                changing_plan_values = any(k in vals for k in ['prospect_plan', 'followup_plan', 'site_visit_plan', 'office_visit_plan'])
                
                if changing_dates or changing_plan_values:
                    # Check if current plan has already started (start_date is today or in the past)
                    # Block editing if plan has started (start_date <= today)
                    if current_start_date and current_start_date <= today:
                        raise ValidationError(
                            f"❌ Cannot Edit Plan That Has Started!\n\n"
                            f"This plan's start date ({current_start_date.strftime('%d %b %Y')}) is today or has already passed. "
                            f"You cannot modify the dates or plan values for plans that have already started.\n\n"
                            f"Please create a new plan for future dates instead."
                        )
                    
                    # Check if new dates are in the past (allow today, block past dates)
                    if changing_dates:
                        # Allow today and future dates, block past dates
                        if start_date_to_check and start_date_to_check < today:
                            raise ValidationError(
                                f"❌ Invalid Start Date!\n\n"
                                f"You cannot set a start date ({start_date_to_check.strftime('%d %b %Y')}) in the past. "
                                f"Please select today ({today.strftime('%d %b %Y')}) or a future date."
                            )
                        
                        # Allow today and future dates, block past dates
                        if end_date_to_check and end_date_to_check < today:
                            raise ValidationError(
                                f"❌ Invalid End Date!\n\n"
                                f"You cannot set an end date ({end_date_to_check.strftime('%d %b %Y')}) in the past. "
                                f"Please select today ({today.strftime('%d %b %Y')}) or a future date."
                            )
                        
                        # Check if start_date is after end_date
                        if start_date_to_check and end_date_to_check and start_date_to_check > end_date_to_check:
                            raise ValidationError(
                                f"❌ Invalid Date Range!\n\n"
                                f"The start date ({start_date_to_check.strftime('%d %b %Y')}) cannot be after the end date ({end_date_to_check.strftime('%d %b %Y')}). "
                                f"Please correct the date range."
                            )
                
                # Validate date overlap if dates or supervisor are being changed
                if 'start_date' in vals or 'end_date' in vals or 'supervisor_id' in vals:
                    # Use the dates we determined above (already converted to date objects)
                    start_date = start_date_to_check
                    end_date = end_date_to_check
                    
                    # Get supervisor_id
                    supervisor_id = vals.get('supervisor_id')
                    if not supervisor_id:
                        supervisor_id = record.supervisor_id.id if record.supervisor_id else False
                    
                    # Ensure we have valid dates and supervisor
                    if not start_date or not end_date:
                        # If dates are missing, use current record dates
                        if not start_date:
                            start_date = record.start_date
                        if not end_date:
                            end_date = record.end_date
                    
                    if start_date and end_date and supervisor_id:
                        # Ensure dates are date objects (not strings)
                        if isinstance(start_date, str):
                            start_date = fields.Date.from_string(start_date)
                        if isinstance(end_date, str):
                            end_date = fields.Date.from_string(end_date)
                        
                        # Ensure supervisor_id is an integer (not a tuple from Many2one)
                        if isinstance(supervisor_id, tuple):
                            supervisor_id = supervisor_id[0]
                        elif isinstance(supervisor_id, list):
                            supervisor_id = supervisor_id[0] if supervisor_id else False
                        
                        if supervisor_id:
                            # Validate date overlap
                            self._validate_date_overlap(start_date, end_date, supervisor_id, exclude_plan_id=record.id)
        
        result = super().write(vals)
        # Auto-update name if dates, wing, or supervisor changed
        if any(key in vals for key in ['start_date', 'end_date', 'wing_id', 'supervisor_id']):
            for record in self:
                # Always update name when dates/wing/supervisor change
                record.name = record._generate_plan_name()
        return result
    
    @api.onchange('start_date', 'end_date', 'wing_id', 'supervisor_id')
    def _onchange_generate_plan_name(self):
        """Auto-generate plan name when dates/wing/supervisor change in form"""
        # Always update name when dates/wing/supervisor change
        self.name = self._generate_plan_name()

    @api.onchange('plan_type')
    def _onchange_plan_type_dates(self):
        """Auto-set date range when plan type changes."""
        today = fields.Date.today()
        if not today:
            return
        if self.plan_type == 'weekly':
            # Next week (Mon-Sun)
            days_until_next_monday = (7 - today.weekday()) % 7
            if days_until_next_monday == 0:
                days_until_next_monday = 7
            start = today + timedelta(days=days_until_next_monday)
            end = start + timedelta(days=6)
            self.start_date = start
            self.end_date = end
        elif self.plan_type == 'monthly':
            # From today to next 30 days
            self.start_date = today
            self.end_date = today + timedelta(days=30)
        elif self.plan_type == 'quarterly':
            # From today to next 90 days
            self.start_date = today
            self.end_date = today + timedelta(days=90)
        # custom -> no automatic change
        self.name = self._generate_plan_name()
    
    @api.depends('start_date', 'end_date', 'plan_type')
    def _compute_period_display(self):
        """Compute period display based on plan type"""
        for plan in self:
            if plan.plan_type == 'quarterly' and plan.start_date and plan.end_date:
                # Format: "Dec 2025 - Feb 2026"
                start_str = plan.start_date.strftime('%b %Y')
                end_str = plan.end_date.strftime('%b %Y')
                plan.period_display = f"{start_str} - {end_str}"
            elif plan.start_date and plan.end_date:
                start_str = plan.start_date.strftime('%d %b %Y')
                end_str = plan.end_date.strftime('%d %b %Y')
                plan.period_display = f"{start_str} to {end_str}"
            else:
                plan.period_display = ""

    @api.depends('supervisor_id')
    def _compute_wing_id(self):
        """Compute wing from supervisor through team relationship"""
        for record in self:
            wing_id = False
            if record.supervisor_id:
                try:
                    # Get supervisor record
                    supervisor_record = self.env['property.sales.supervisor'].search([
                        ('name', '=', record.supervisor_id.id)
                    ], limit=1)

                    if supervisor_record:
                        # Find the team that has this supervisor
                        team = self.env['property.sales.team'].search([
                            ('supervisor_ids', 'in', supervisor_record.id)
                        ], limit=1)

                        if team:
                            # Force recompute team's wing_id
                            team._compute_wing_id()
                            if team.wing_id:
                                wing_id = team.wing_id.id
                            else:
                                # Try to find wing directly through wing_team_rel
                                self.env.cr.execute("""
                                                    SELECT w.id
                                                    FROM property_sales_wing w
                                                             JOIN property_wing_team_rel wtr ON wtr.wing_id = w.id
                                                    WHERE wtr.team_id = %s LIMIT 1
                                                    """, (team.id,))
                                result = self.env.cr.fetchone()
                                if result:
                                    wing_id = result[0]
                        else:
                            # Try to find wing through wing_team_rel using supervisor
                            self.env.cr.execute("""
                                                SELECT w.id
                                                FROM property_sales_wing w
                                                         JOIN property_wing_team_rel wtr ON wtr.wing_id = w.id
                                                         JOIN property_team_supervisor_rel tsr ON tsr.team_id = wtr.team_id
                                                WHERE tsr.supervisor_id = %s LIMIT 1
                                                """, (supervisor_record.id,))

                            result = self.env.cr.fetchone()
                            if result:
                                wing_id = result[0]

                except Exception as e:
                    _logger.warning(f"Error computing wing for supervisor: {e}")
            record.wing_id = wing_id

    @api.depends('site_visit_plan', 'office_visit_plan')
    def _compute_total_plan(self):
        for plan in self:
            plan.total_visit_plan = plan.site_visit_plan + plan.office_visit_plan

    @api.depends('opening_stock_residence_qty_plan', 'opening_stock_residence_value_plan',
                 'opening_stock_shops_qty_plan', 'opening_stock_shops_value_plan')
    def _compute_opening_stock_plan_total(self):
        for plan in self:
            plan.opening_stock_total_qty_plan = (plan.opening_stock_residence_qty_plan or 0) + (plan.opening_stock_shops_qty_plan or 0)
            plan.opening_stock_total_value_plan = (plan.opening_stock_residence_value_plan or 0.0) + (plan.opening_stock_shops_value_plan or 0.0)

    @api.depends('actual_prospects', 'prospect_plan',
                 'actual_followups', 'followup_plan',
                 'actual_site_visits', 'site_visit_plan',
                 'actual_office_visits', 'office_visit_plan',
                 'actual_total_visits', 'total_visit_plan',
                 'actual_unit_reservations', 'unit_reservation_plan',
                 'actual_deals_closed', 'deals_closed_plan',
                 'actual_cash_collected', 'cash_collected_plan',
                 'actual_total_deal_value', 'total_deal_value_plan',
                 'actual_conversion', 'conversion_plan',
                 'actual_iar', 'iar_plan')
    def _compute_percentages(self):
        for plan in self:
            try:
                # Prospects percentage
                plan.prospect_percentage = self._calculate_percentage(plan.actual_prospects, plan.prospect_plan)
                # Follow-ups percentage
                plan.followup_percentage = self._calculate_percentage(plan.actual_followups, plan.followup_plan)
                # Site visits percentage
                plan.site_visit_percentage = self._calculate_percentage(plan.actual_site_visits, plan.site_visit_plan)
                # Office visits percentage
                plan.office_visit_percentage = self._calculate_percentage(plan.actual_office_visits,
                                                                          plan.office_visit_plan)
                # Total visits percentage
                plan.total_visit_percentage = self._calculate_percentage(plan.actual_total_visits,
                                                                         plan.total_visit_plan)
                # Unit reservations percentage
                plan.unit_reservation_percentage = self._calculate_percentage(plan.actual_unit_reservations,
                                                                              plan.unit_reservation_plan)
                # Deals closed percentage
                plan.deals_closed_percentage = self._calculate_percentage(plan.actual_deals_closed,
                                                                          plan.deals_closed_plan)
                # Cash collected percentage
                plan.cash_collected_percentage = self._calculate_percentage(plan.actual_cash_collected,
                                                                            plan.cash_collected_plan)
                # Total deal value percentage
                plan.total_deal_value_percentage = self._calculate_percentage(plan.actual_total_deal_value,
                                                                              plan.total_deal_value_plan)
                # Conversion percentage (special calculation)
                if plan.conversion_plan > 0:
                    plan.conversion_percentage = min(100.0, (plan.actual_conversion / plan.conversion_plan) * 100)
                else:
                    plan.conversion_percentage = 0.0
                # IAR percentage (special calculation)
                if plan.iar_plan > 0:
                    plan.iar_percentage = min(100.0, (plan.actual_iar / plan.iar_plan) * 100)
                else:
                    plan.iar_percentage = 0.0
            except Exception as e:
                _logger.error(f"Error computing percentages: {e}")
                # Reset all percentages to 0
                for field in ['prospect_percentage', 'followup_percentage', 'site_visit_percentage',
                              'office_visit_percentage', 'total_visit_percentage', 'unit_reservation_percentage',
                              'deals_closed_percentage', 'cash_collected_percentage', 'total_deal_value_percentage',
                              'conversion_percentage', 'iar_percentage']:
                    setattr(plan, field, 0.0)

    def _calculate_percentage(self, actual, plan):
        """Helper method to calculate percentage"""
        if plan > 0:
            return min(100.0, (actual / plan) * 100)
        return 0.0

    @api.depends('actual_prospects', 'previous_prospects',
                 'actual_followups', 'previous_followups',
                 'actual_site_visits', 'previous_site_visits',
                 'actual_office_visits', 'previous_office_visits',
                 'actual_total_visits', 'previous_total_visits',
                 'actual_unit_reservations', 'previous_unit_reservations',
                 'actual_deals_closed', 'previous_deals_closed',
                 'actual_cash_collected', 'previous_cash_collected',
                 'actual_total_deal_value', 'previous_total_deal_value')
    def _compute_differences(self):
        """Compute differences between current and previous week"""
        for plan in self:
            try:
                plan.prospect_difference = plan.actual_prospects - plan.previous_prospects
                plan.followup_difference = plan.actual_followups - plan.previous_followups
                plan.site_visit_difference = plan.actual_site_visits - plan.previous_site_visits
                plan.office_visit_difference = plan.actual_office_visits - plan.previous_office_visits
                plan.total_visit_difference = plan.actual_total_visits - plan.previous_total_visits
                plan.unit_reservation_difference = plan.actual_unit_reservations - plan.previous_unit_reservations
                plan.deals_closed_difference = plan.actual_deals_closed - plan.previous_deals_closed
                plan.cash_collected_difference = plan.actual_cash_collected - plan.previous_cash_collected
                plan.total_deal_value_difference = plan.actual_total_deal_value - plan.previous_total_deal_value
            except Exception as e:
                _logger.error(f"Error computing differences: {e}")
                for field in ['prospect_difference', 'followup_difference', 'site_visit_difference',
                              'office_visit_difference', 'total_visit_difference', 'unit_reservation_difference',
                              'deals_closed_difference', 'cash_collected_difference', 'total_deal_value_difference']:
                    setattr(plan, field, 0)

    # ========== DATA QUERY METHODS ==========
    def _get_user_ids_for_supervisor(self):
        """Get all user IDs for this plan's supervisor"""
        user_ids = []
        try:
            if self.supervisor_id:
                user_ids.append(self.supervisor_id.id)

                # Get salespersons under this supervisor
                if 'property.salesperson.mapping' in self.env:
                    salespersons = self.env['property.salesperson.mapping'].search([
                        ('supervisor_id', '=', self.supervisor_id.id)
                    ])
                    for sp in salespersons:
                        if sp.user_id:
                            user_ids.append(sp.user_id.id)
        except Exception as e:
            _logger.error(f"Error getting user IDs for supervisor: {e}")

        return list(set(user_ids))

    def _get_temer_lead_counts(self, start_date, end_date, user_ids=None):
        """Get lead counts from temer_lead table"""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            query_prospects = """
                              SELECT COUNT(*) as count
                              FROM temer_lead
                              WHERE create_date >= %s
                                AND create_date <= %s
                                AND state IN ('prospect' \
                                  , 'reservation' \
                                  , 'won' \
                                  , 'new_lead') \
                              """

            query_followups = """
                              SELECT COUNT(*) as count
                              FROM temer_lead
                              WHERE create_date >= %s
                                AND create_date <= %s
                                AND state NOT IN ('prospect' \
                                  , 'reservation' \
                                  , 'won' \
                                  , 'new_lead') \
                              """

            params = [start_datetime, end_datetime]

            if user_ids:
                query_prospects += " AND user_id IN %s"
                query_followups += " AND user_id IN %s"
                params_with_users = params + [tuple(user_ids)]

                self.env.cr.execute(query_prospects, params_with_users)
                result_prospects = self.env.cr.fetchone()

                self.env.cr.execute(query_followups, params_with_users)
                result_followups = self.env.cr.fetchone()
            else:
                self.env.cr.execute(query_prospects, params)
                result_prospects = self.env.cr.fetchone()

                self.env.cr.execute(query_followups, params)
                result_followups = self.env.cr.fetchone()

            prospects = result_prospects[0] if result_prospects else 0
            followups = result_followups[0] if result_followups else 0

            return {
                'prospect': int(prospects),
                'follow_up': int(followups)
            }
        except Exception as e:
            _logger.error(f"Error getting temer lead counts: {e}")
            return {'prospect': 0, 'follow_up': 0}

    def _get_temer_activity_counts(self, start_date, end_date, user_ids=None):
        """Get activity counts"""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Check if table exists
            query_check = """
                          SELECT EXISTS (SELECT 1 \
                                         FROM information_schema.tables \
                                         WHERE table_name = 'temer_lead_activity_wizard') \
                          """
            self.env.cr.execute(query_check)
            table_exists = self.env.cr.fetchone()[0]

            if not table_exists:
                return {'site_visit': 0, 'office_visit': 0}

            # Get site visits
            query_site_visits = """
                                SELECT COUNT(*) as count
                                FROM temer_lead_activity_wizard
                                WHERE create_date >= %s
                                  AND create_date <= %s
                                  AND activity_type = 'site_visit' \
                                """

            # Get office visits
            query_office_visits = """
                                  SELECT COUNT(*) as count
                                  FROM temer_lead_activity_wizard
                                  WHERE create_date >= %s
                                    AND create_date <= %s
                                    AND activity_type = 'office_visit' \
                                  """

            params = [start_datetime, end_datetime]

            if user_ids:
                # Get lead IDs for these users
                query_lead_ids = "SELECT id FROM temer_lead WHERE user_id IN %s"
                self.env.cr.execute(query_lead_ids, (tuple(user_ids),))
                lead_results = self.env.cr.fetchall()

                if lead_results:
                    lead_ids = [str(lead[0]) for lead in lead_results]
                    query_site_visits += " AND lead_id IN %s"
                    query_office_visits += " AND lead_id IN %s"

                    params_site = params + [tuple(lead_ids)]
                    params_office = params + [tuple(lead_ids)]

                    self.env.cr.execute(query_site_visits, params_site)
                    result_site_visits = self.env.cr.fetchone()

                    self.env.cr.execute(query_office_visits, params_office)
                    result_office_visits = self.env.cr.fetchone()
                else:
                    return {'site_visit': 0, 'office_visit': 0}
            else:
                self.env.cr.execute(query_site_visits, params)
                result_site_visits = self.env.cr.fetchone()

                self.env.cr.execute(query_office_visits, params)
                result_office_visits = self.env.cr.fetchone()

            site_visits = result_site_visits[0] if result_site_visits else 0
            office_visits = result_office_visits[0] if result_office_visits else 0

            return {
                'site_visit': int(site_visits),
                'office_visit': int(office_visits)
            }
        except Exception as e:
            _logger.error(f"Error getting temer activity counts: {e}")
            return {'site_visit': 0, 'office_visit': 0}

    def _get_reservation_counts(self, start_date, end_date, user_ids=None):
        """Get unit reservation counts"""
        try:
            query = """
                SELECT COUNT(DISTINCT pr.id) as count
                FROM property_reservation pr
                JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                WHERE DATE(pr.create_date) BETWEEN %s AND %s
                  AND pr.status IN ('reserved', 'requested', 'pending_sales')
                  AND prc.reservation_type IN ('quick', 'regular')
            """
            params = [start_date, end_date]

            if user_ids:
                query += " AND pr.salesperson_ids IN %s"
                params.append(tuple(user_ids))

            self.env.cr.execute(query, params)
            result = self.env.cr.fetchone()
            return result[0] if result else 0
        except Exception as e:
            _logger.error(f"Error getting reservation counts: {e}")
            return 0

    def _get_deal_counts(self, start_date, end_date, user_ids=None):
        """Get deal counts (sold qty)"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM property_sale ps
                WHERE DATE(ps.create_date) BETWEEN %s AND %s
                  AND ps.state = 'confirm'
            """
            params = [start_date, end_date]

            if user_ids:
                query += " AND ps.create_uid IN %s"
                params.append(tuple(user_ids))

            self.env.cr.execute(query, params)
            result = self.env.cr.fetchone()
            return result[0] if result else 0
        except Exception as e:
            _logger.error(f"Error getting deal counts: {e}")
            return 0

    def _get_cash_collected_amount(self, start_date, end_date, user_ids=None):
        """Sum approved reservation payments (advance paid) within date range"""
        try:
            query = """
                SELECT COALESCE(SUM(prp.amount), 0)
                FROM property_reservation_payment prp
                JOIN property_reservation pr ON pr.id = prp.reservation_id
                JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                WHERE prp.payment_status = 'approved'
                  AND DATE(prp.transaction_date) BETWEEN %s AND %s
                  AND pr.status NOT IN ('canceled', 'expired')
                  AND prc.reservation_type IN ('quick', 'regular')
            """
            params = [start_date, end_date]
            if user_ids:
                query += " AND pr.salesperson_ids IN %s"
                params.append(tuple(user_ids))

            self.env.cr.execute(query, params)
            result = self.env.cr.fetchone()
            return result[0] if result and result[0] else 0.0
        except Exception as e:
            _logger.error(f"Error getting cash collected amount: {e}")
            return 0.0

    def _get_total_deal_value(self, start_date, end_date, user_ids=None):
        """Sum sold deal value within date range"""
        try:
            query = """
                SELECT COALESCE(SUM(COALESCE(ps.sale_price, 0)), 0)
                FROM property_sale ps
                WHERE DATE(ps.create_date) BETWEEN %s AND %s
                  AND ps.state = 'confirm'
            """
            params = [start_date, end_date]
            if user_ids:
                query += " AND ps.create_uid IN %s"
                params.append(tuple(user_ids))

            self.env.cr.execute(query, params)
            result = self.env.cr.fetchone()
            return result[0] if result and result[0] else 0.0
        except Exception as e:
            _logger.error(f"Error getting total deal value: {e}")
            return 0.0

    def _get_opening_stock_values(self, date_from):
        """Fetch opening stock values based on available properties before date_from"""
        try:
            query = """
                SELECT 
                    COUNT(CASE WHEN property_type = 'residence' THEN 1 END) as residence_qty,
                    COALESCE(SUM(CASE WHEN property_type = 'residence' THEN unit_price ELSE 0 END), 0) as residence_value,
                    COUNT(CASE WHEN property_type = 'shop' THEN 1 END) as shops_qty,
                    COALESCE(SUM(CASE WHEN property_type = 'shop' THEN unit_price ELSE 0 END), 0) as shops_value
                FROM property_property
                WHERE state = 'available'
                  AND (create_date < %s OR create_date IS NULL)
            """
            self.env.cr.execute(query, (datetime.combine(date_from, datetime.min.time()),))
            result = self.env.cr.fetchone()
            if not result:
                return {
                    'residence_qty': 0,
                    'residence_value': 0.0,
                    'shops_qty': 0,
                    'shops_value': 0.0,
                }
            return {
                'residence_qty': result[0] or 0,
                'residence_value': result[1] or 0.0,
                'shops_qty': result[2] or 0,
                'shops_value': result[3] or 0.0,
            }
        except Exception as e:
            _logger.error(f"Error getting opening stock values: {e}")
            return {
                'residence_qty': 0,
                'residence_value': 0.0,
                'shops_qty': 0,
                'shops_value': 0.0,
            }

    @api.model
    def generate_supervisor_report_data(self, supervisor_id, start_date, end_date):
        """Generate report data for supervisor (called from JS)"""
        try:
            start_date = fields.Date.from_string(start_date)
            end_date = fields.Date.from_string(end_date)

            # Get supervisor's plans in date range
            plans = self.search([
                ('supervisor_id', '=', supervisor_id),
                ('start_date', '<=', end_date),
                ('end_date', '>=', start_date),
                ('state', '=', 'completed')
            ])

            # Get all salespersons under this supervisor
            supervisor_record = self.env['property.sales.supervisor'].search([
                ('name', '=', supervisor_id)
            ], limit=1)

            salesperson_ids = []
            if supervisor_record:
                salesperson_mappings = self.env['property.salesperson.mapping'].search([
                    ('supervisor_id', '=', supervisor_record.id)
                ])
                salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # All user IDs (supervisor + salespersons)
            all_user_ids = [supervisor_id] + salesperson_ids

            # Calculate metrics
            result = self._calculate_metrics(plans, all_user_ids, start_date, end_date, 'supervisor')

            return result

        except Exception as e:
            _logger.error(f"Error generating supervisor report: {e}")
            return {'error': str(e)}

    @api.model
    def generate_wing_report_data(self, wing_id, start_date, end_date):
        """Generate report data for wing (called from JS)"""
        try:
            start_date = fields.Date.from_string(start_date)
            end_date = fields.Date.from_string(end_date)

            # Get all supervisors in this wing
            supervisors = self.env['property.sales.supervisor'].search([
                ('sales_team_id.wing_id', '=', wing_id)
            ])
            supervisor_ids = supervisors.mapped('name.id')

            # Get all salespersons under these supervisors
            salesperson_mappings = self.env['property.salesperson.mapping'].search([
                ('supervisor_id.name', 'in', supervisor_ids)
            ])
            salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # All user IDs
            all_user_ids = list(set(list(supervisor_ids) + salesperson_ids))

            # Get all plans for these supervisors
            plans = self.search([
                ('supervisor_id', 'in', supervisor_ids),
                ('start_date', '<=', end_date),
                ('end_date', '>=', start_date),
                ('state', '=', 'completed')
            ])

            # Calculate metrics
            result = self._calculate_metrics(plans, all_user_ids, start_date, end_date, 'wing')

            return result

        except Exception as e:
            _logger.error(f"Error generating wing report: {e}")
            return {'error': str(e)}

    def _calculate_metrics(self, plans, user_ids, start_date, end_date, report_type):
        """Calculate all metrics for the report"""
        result = {}

        # Define metric fields
        metric_fields = [
            'prospects', 'followups', 'site_visits', 'office_visits',
            'total_visits', 'unit_reservations', 'deals_closed',
            'cash_collected', 'total_deal_value', 'conversion', 'iar'
        ]

        for metric in metric_fields:
            metric_key = metric.replace('_', '')
            plan_field = f"{metric}_plan"
            actual_field = f"actual_{metric}"
            previous_field = f"previous_{metric}"
            diff_field = f"{metric}_difference"
            perc_field = f"{metric}_percentage"

            # Calculate plan total (sum of plans)
            plan_total = sum(plans.mapped(plan_field)) if plans else 0

            # Calculate actual (from database)
            actual_total = self._get_actual_count(metric, start_date, end_date, user_ids)

            # Calculate previous week
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
            previous_total = self._get_actual_count(metric, prev_start, prev_end, user_ids)

            # Calculate difference and percentage
            difference = actual_total - previous_total
            percentage = 0
            if plan_total > 0:
                percentage = min(100.0, (actual_total / plan_total) * 100)

            result[metric_key] = {
                'plan': plan_total if metric not in ['conversion', 'iar'] else float(f"{plan_total:.2f}"),
                'actual': actual_total if metric not in ['conversion', 'iar'] else float(f"{actual_total:.2f}"),
                'previous': previous_total if metric not in ['conversion', 'iar'] else float(f"{previous_total:.2f}"),
                'difference': difference if metric not in ['conversion', 'iar'] else '-',
                'percentage': float(f"{percentage:.1f}")
            }

        return result

    def _get_actual_count(self, metric, start_date, end_date, user_ids):
        """Get actual count from database for a specific metric"""
        # Implement based on your database structure
        # This should query your temer_lead and other tables
        # Return appropriate count based on metric type
        return 0  # Replace with actual query
    @api.depends('start_date', 'end_date', 'supervisor_id')
    def _compute_actual_metrics(self):
        """Compute actual metrics from database"""
        for plan in self:
            try:
                if not plan.start_date or not plan.end_date or not plan.supervisor_id:
                    continue

                user_ids = plan._get_user_ids_for_supervisor()
                if not user_ids:
                    continue

                # Get basic counts
                temer_counts = plan._get_temer_lead_counts(plan.start_date, plan.end_date, user_ids)
                temer_activities = plan._get_temer_activity_counts(plan.start_date, plan.end_date, user_ids)

                # Set basic metrics
                plan.actual_prospects = temer_counts.get('prospect', 0)
                plan.actual_followups = temer_counts.get('follow_up', 0)
                plan.actual_site_visits = temer_activities.get('site_visit', 0)
                plan.actual_office_visits = temer_activities.get('office_visit', 0)
                plan.actual_total_visits = plan.actual_site_visits + plan.actual_office_visits

                # Get new metrics
                plan.actual_unit_reservations = plan._get_reservation_counts(plan.start_date, plan.end_date, user_ids)
                plan.actual_deals_closed = plan._get_deal_counts(plan.start_date, plan.end_date, user_ids)
                plan.actual_cash_collected = plan._get_cash_collected_amount(plan.start_date, plan.end_date, user_ids)
                plan.actual_total_deal_value = plan._get_total_deal_value(plan.start_date, plan.end_date, user_ids)

                # Opening stock (actual)
                opening_stock = plan._get_opening_stock_values(plan.start_date)
                plan.actual_opening_stock_residence_qty = opening_stock['residence_qty']
                plan.actual_opening_stock_residence_value = opening_stock['residence_value']
                plan.actual_opening_stock_shops_qty = opening_stock['shops_qty']
                plan.actual_opening_stock_shops_value = opening_stock['shops_value']
                plan.actual_opening_stock_total_qty = opening_stock['residence_qty'] + opening_stock['shops_qty']
                plan.actual_opening_stock_total_value = opening_stock['residence_value'] + opening_stock['shops_value']

                # Calculate conversion (ratio, not percent)
                if plan.actual_prospects > 0:
                    plan.actual_conversion = (plan.actual_deals_closed / plan.actual_prospects)
                else:
                    plan.actual_conversion = 0.0

                # IAR (Inventory Absorption Rate) based on estimated opening stock value
                if plan.actual_opening_stock_total_value > 0:
                    plan.actual_iar = (plan.actual_total_deal_value / plan.actual_opening_stock_total_value) * 100
                else:
                    plan.actual_iar = 0.0

            except Exception as e:
                _logger.error(f"Error computing actual metrics for plan {plan.id}: {e}")

    @api.depends('start_date', 'supervisor_id')
    def _compute_previous_metrics(self):
        """Compute previous week metrics"""
        for plan in self:
            try:
                if not plan.start_date or not plan.supervisor_id:
                    continue

                # Calculate previous week
                previous_start = plan.start_date - timedelta(days=7)
                previous_end = plan.start_date - timedelta(days=1)

                user_ids = plan._get_user_ids_for_supervisor()
                if not user_ids:
                    continue

                # Get previous week counts
                temer_counts = plan._get_temer_lead_counts(previous_start, previous_end, user_ids)
                temer_activities = plan._get_temer_activity_counts(previous_start, previous_end, user_ids)

                # Set previous metrics
                plan.previous_prospects = temer_counts.get('prospect', 0)
                plan.previous_followups = temer_counts.get('follow_up', 0)
                plan.previous_site_visits = temer_activities.get('site_visit', 0)
                plan.previous_office_visits = temer_activities.get('office_visit', 0)
                plan.previous_total_visits = plan.previous_site_visits + plan.previous_office_visits

                # Get previous new metrics
                plan.previous_unit_reservations = plan._get_reservation_counts(previous_start, previous_end, user_ids)
                plan.previous_deals_closed = plan._get_deal_counts(previous_start, previous_end, user_ids)
                plan.previous_cash_collected = plan._get_cash_collected_amount(previous_start, previous_end, user_ids)
                plan.previous_total_deal_value = plan._get_total_deal_value(previous_start, previous_end, user_ids)

            except Exception as e:
                _logger.error(f"Error computing previous metrics: {e}")

    # ========== ACTION METHODS ==========
    def action_complete(self):
        for record in self:
            record.state = 'completed'

    def action_draft(self):
        for record in self:
            record.state = 'draft'

    def action_view_report(self):
        """Open report view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Report - {self.name}',
            'res_model': 'sales.plan',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {'form_view_ref': 'sales_plan_module.view_sales_plan_report_form'},
        }

    def action_refresh_metrics(self):
        """Refresh all computed metrics"""
        for record in self:
            record._compute_actual_metrics()
            record._compute_previous_metrics()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Refresh Complete',
                'message': 'All metrics have been refreshed.',
                'type': 'success',
            }
        }




# ========== WIZARD MODELS FOR REPORTS ==========

class WingPlanReportWizard(models.TransientModel):
    _name = 'wing.plan.report.wizard'  # MUST match XML
    _description = 'Wing Plan Report Wizard'

    wing_id = fields.Many2one('property.sales.wing', string='Wing', required=True)
    start_date = fields.Date(string='From Date', required=True, default=fields.Date.today())
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.today())

    def action_generate_report(self):
        """Generate wing plan report - UPDATED VERSION"""
        # Get all supervisors in this wing
        supervisors = self.env['property.sales.supervisor'].search([
            ('sales_team_id.wing_id', '=', self.wing_id.id)
        ])
        supervisor_ids = supervisors.mapped('name.id')

        # Get plans for these supervisors in the date range
        plans = self.env['sales.plan'].search([
            ('supervisor_id', 'in', supervisor_ids),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('state', 'in', ['confirmed', 'in_progress', 'completed'])
        ])

        if not plans:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Data',
                    'message': 'No plans found for the selected wing in this date range.',
                    'type': 'warning',
                }
            }

        # Return action to show report
        return {
            'type': 'ir.actions.act_window',
            'name': f'Wing Plan Report - {self.wing_id.name}',
            'res_model': 'sales.plan',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', plans.ids)],
            'context': {
                'search_default_group_supervisor': 1,
                'default_wing_id': self.wing_id.id,
            },
        }


class SupervisorPlanReportWizard(models.TransientModel):
    _name = 'supervisor.plan.report.wizard'  # MUST match XML
    _description = 'Supervisor Plan Report Wizard'

    supervisor_id = fields.Many2one('res.users', string='Supervisor', required=True)
    start_date = fields.Date(string='From Date', required=True, default=fields.Date.today())
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.today())

    def action_generate_report(self):
        """Generate supervisor plan report - UPDATED VERSION"""
        # Get plans for this supervisor in the date range
        plans = self.env['sales.plan'].search([
            ('supervisor_id', '=', self.supervisor_id.id),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('state', 'in', ['confirmed', 'in_progress', 'completed'])
        ])

        if not plans:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Data',
                    'message': 'No plans found for the selected supervisor in this date range.',
                    'type': 'warning',
                }
            }

        # Return action to show report
        return {
            'type': 'ir.actions.act_window',
            'name': f'Supervisor Plan Report - {self.supervisor_id.name}',
            'res_model': 'sales.plan',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', plans.ids)],
            'context': {
                'search_default_group_plan_type': 1,
                'default_supervisor_id': self.supervisor_id.id,
            },
        }

    # ========== PLAN REPORT ACTION MODELS ==========

    class WingPlanReportAction(models.TransientModel):
        _name = 'wing.plan.report.action'
        _description = 'Wing Plan Report Action'

        wing_id = fields.Many2one('property.sales.wing', string='Wing', required=True)
        start_date = fields.Date(string='From Date', required=True, default=fields.Date.today())
        end_date = fields.Date(string='To Date', required=True, default=fields.Date.today())

        def action_view_wing_report(self):
            """Generate aggregated wing report"""
            self.ensure_one()

            # Get all supervisors in this wing
            supervisors = self.env['property.sales.supervisor'].search([
                ('sales_team_id.wing_id', '=', self.wing_id.id)
            ])

            supervisor_ids = supervisors.mapped('name.id')

            # Get all sales plans for these supervisors in date range
            plans = self.env['sales.plan'].search([
                ('supervisor_id', 'in', supervisor_ids),
                ('start_date', '<=', self.end_date),
                ('end_date', '>=', self.start_date),
                ('state', '=', 'completed')
            ])

            if not plans:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Data',
                        'message': 'No plans found for the selected wing in this date range.',
                        'type': 'warning',
                    }
                }

            # Calculate aggregated metrics
            aggregated_data = self._calculate_aggregated_metrics(plans, supervisor_ids)

            # Create a virtual plan for display
            virtual_plan_id = self._create_virtual_wing_plan(aggregated_data)

            # Open the report view
            return {
                'type': 'ir.actions.act_window',
                'name': f'Wing Report - {self.wing_id.name} ({self.start_date} to {self.end_date})',
                'res_model': 'sales.plan',
                'res_id': virtual_plan_id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {'form_view_ref': 'sales_plan_module.view_sales_plan_report_form'},
            }

        def _calculate_aggregated_metrics(self, plans, supervisor_ids):
            """Calculate aggregated metrics for all supervisors in wing"""
            aggregated = {
                'name': f'Wing Aggregated Report',
                'supervisor_id': False,
                'wing_id': self.wing_id.id,

                # Plan totals
                'prospect_plan': sum(plans.mapped('prospect_plan')),
                'followup_plan': sum(plans.mapped('followup_plan')),
                'site_visit_plan': sum(plans.mapped('site_visit_plan')),
                'office_visit_plan': sum(plans.mapped('office_visit_plan')),
                'total_visit_plan': sum(plans.mapped('total_visit_plan')),
                'unit_reservation_plan': sum(plans.mapped('unit_reservation_plan')),
                'deals_closed_plan': sum(plans.mapped('deals_closed_plan')),
                'cash_collected_plan': sum(plans.mapped('cash_collected_plan')),
                'total_deal_value_plan': sum(plans.mapped('total_deal_value_plan')),
                'conversion_plan': plans and sum(plans.mapped('conversion_plan')) / len(plans) or 0,
                'iar_plan': plans and sum(plans.mapped('iar_plan')) / len(plans) or 0,
                'opening_stock_residence_qty_plan': sum(plans.mapped('opening_stock_residence_qty_plan')),
                'opening_stock_residence_value_plan': sum(plans.mapped('opening_stock_residence_value_plan')),
                'opening_stock_shops_qty_plan': sum(plans.mapped('opening_stock_shops_qty_plan')),
                'opening_stock_shops_value_plan': sum(plans.mapped('opening_stock_shops_value_plan')),
                'opening_stock_total_qty_plan': sum(plans.mapped('opening_stock_total_qty_plan')),
                'opening_stock_total_value_plan': sum(plans.mapped('opening_stock_total_value_plan')),

                # Actual totals (calculated from all salespersons under these supervisors)
                'actual_prospects': 0,
                'actual_followups': 0,
                'actual_site_visits': 0,
                'actual_office_visits': 0,
                'actual_total_visits': 0,
                'actual_unit_reservations': 0,
                'actual_deals_closed': 0,
                'actual_cash_collected': 0.0,
                'actual_total_deal_value': 0.0,
                'actual_conversion': 0.0,
                'actual_iar': 0.0,
                'actual_opening_stock_residence_qty': 0,
                'actual_opening_stock_residence_value': 0.0,
                'actual_opening_stock_shops_qty': 0,
                'actual_opening_stock_shops_value': 0.0,
                'actual_opening_stock_total_qty': 0,
                'actual_opening_stock_total_value': 0.0,

                # Previous week totals
                'previous_prospects': 0,
                'previous_followups': 0,
                'previous_site_visits': 0,
                'previous_office_visits': 0,
                'previous_total_visits': 0,
                'previous_unit_reservations': 0,
                'previous_deals_closed': 0,
                'previous_cash_collected': 0.0,
                'previous_total_deal_value': 0.0,

                # Remarks
                'prospect_remark': 'Wing Aggregated Report',
                'followup_remark': 'Wing Aggregated Report',
                'site_visit_remark': 'Wing Aggregated Report',
                'office_visit_remark': 'Wing Aggregated Report',
                'total_visit_remark': 'Wing Aggregated Report',
                'unit_reservation_remark': 'Wing Aggregated Report',
                'deals_closed_remark': 'Wing Aggregated Report',
                'cash_collected_remark': 'Wing Aggregated Report',
                'total_deal_value_remark': 'Wing Aggregated Report',
                'conversion_remark': 'Wing Aggregated Report',
                'iar_remark': 'Wing Aggregated Report',
            }

            # Get all salespersons under these supervisors
            salesperson_mappings = self.env['property.salesperson.mapping'].search([
                ('supervisor_id.name', 'in', supervisor_ids)
            ])
            salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # Calculate actual metrics for all salespersons
            all_user_ids = list(set(list(supervisor_ids) + salesperson_ids))

            if all_user_ids:
                # Calculate actual metrics
                aggregated['actual_prospects'] = self._get_lead_count(self.start_date, self.end_date, all_user_ids,
                                                                      'prospect')
                aggregated['actual_followups'] = self._get_lead_count(self.start_date, self.end_date, all_user_ids,
                                                                      'follow_up')
                aggregated['actual_site_visits'] = self._get_activity_count(self.start_date, self.end_date,
                                                                            all_user_ids, 'site_visit')
                aggregated['actual_office_visits'] = self._get_activity_count(self.start_date, self.end_date,
                                                                              all_user_ids, 'office_visit')
                aggregated['actual_total_visits'] = aggregated['actual_site_visits'] + aggregated[
                    'actual_office_visits']
                aggregated['actual_unit_reservations'] = self._get_reservation_count(self.start_date, self.end_date,
                                                                                     all_user_ids)
                aggregated['actual_deals_closed'] = self._get_deal_count(self.start_date, self.end_date, all_user_ids)
                aggregated['actual_cash_collected'] = self.env['sales.plan']._get_cash_collected_amount(
                    self.start_date, self.end_date, all_user_ids
                )
                aggregated['actual_total_deal_value'] = self.env['sales.plan']._get_total_deal_value(
                    self.start_date, self.end_date, all_user_ids
                )

                opening_stock = self.env['sales.plan']._get_opening_stock_values(self.start_date)
                aggregated['actual_opening_stock_residence_qty'] = opening_stock['residence_qty']
                aggregated['actual_opening_stock_residence_value'] = opening_stock['residence_value']
                aggregated['actual_opening_stock_shops_qty'] = opening_stock['shops_qty']
                aggregated['actual_opening_stock_shops_value'] = opening_stock['shops_value']
                aggregated['actual_opening_stock_total_qty'] = opening_stock['residence_qty'] + opening_stock['shops_qty']
                aggregated['actual_opening_stock_total_value'] = opening_stock['residence_value'] + opening_stock['shops_value']

                # Calculate previous week metrics
                prev_start = self.start_date - timedelta(days=7)
                prev_end = self.start_date - timedelta(days=1)

                aggregated['previous_prospects'] = self._get_lead_count(prev_start, prev_end, all_user_ids, 'prospect')
                aggregated['previous_followups'] = self._get_lead_count(prev_start, prev_end, all_user_ids, 'follow_up')
                aggregated['previous_site_visits'] = self._get_activity_count(prev_start, prev_end, all_user_ids,
                                                                              'site_visit')
                aggregated['previous_office_visits'] = self._get_activity_count(prev_start, prev_end, all_user_ids,
                                                                                'office_visit')
                aggregated['previous_total_visits'] = aggregated['previous_site_visits'] + aggregated[
                    'previous_office_visits']
                aggregated['previous_unit_reservations'] = self._get_reservation_count(prev_start, prev_end,
                                                                                       all_user_ids)
                aggregated['previous_deals_closed'] = self._get_deal_count(prev_start, prev_end, all_user_ids)
                aggregated['previous_cash_collected'] = self.env['sales.plan']._get_cash_collected_amount(
                    prev_start, prev_end, all_user_ids
                )
                aggregated['previous_total_deal_value'] = self.env['sales.plan']._get_total_deal_value(
                    prev_start, prev_end, all_user_ids
                )

                # Calculate conversion (ratio, not percent)
                if aggregated['actual_prospects'] > 0:
                    aggregated['actual_conversion'] = (aggregated['actual_deals_closed'] / aggregated['actual_prospects'])
                if aggregated['actual_opening_stock_total_value'] > 0:
                    aggregated['actual_iar'] = (aggregated['actual_total_deal_value'] / aggregated[
                        'actual_opening_stock_total_value']) * 100

            return aggregated

        def _create_virtual_wing_plan(self, data):
            """Create a temporary virtual plan for display"""
            virtual_plan = self.env['sales.plan'].create({
                'name': data['name'],
                'plan_type': 'monthly',
                'start_date': self.start_date,
                'end_date': self.end_date,
                'supervisor_id': data['supervisor_id'],
                'wing_id': data['wing_id'],
                'state': 'completed',

                # Plan targets
                'prospect_plan': data['prospect_plan'],
                'followup_plan': data['followup_plan'],
                'site_visit_plan': data['site_visit_plan'],
                'office_visit_plan': data['office_visit_plan'],
                'total_visit_plan': data['total_visit_plan'],
                'unit_reservation_plan': data['unit_reservation_plan'],
                'deals_closed_plan': data['deals_closed_plan'],
                'cash_collected_plan': data['cash_collected_plan'],
                'total_deal_value_plan': data['total_deal_value_plan'],
                'conversion_plan': data['conversion_plan'],
                'iar_plan': data['iar_plan'],
                'opening_stock_residence_qty_plan': data.get('opening_stock_residence_qty_plan', 0),
                'opening_stock_residence_value_plan': data.get('opening_stock_residence_value_plan', 0.0),
                'opening_stock_shops_qty_plan': data.get('opening_stock_shops_qty_plan', 0),
                'opening_stock_shops_value_plan': data.get('opening_stock_shops_value_plan', 0.0),
                'opening_stock_total_qty_plan': data.get('opening_stock_total_qty_plan', 0),
                'opening_stock_total_value_plan': data.get('opening_stock_total_value_plan', 0.0),
                'opening_stock_residence_qty_plan': data.get('opening_stock_residence_qty_plan', 0),
                'opening_stock_residence_value_plan': data.get('opening_stock_residence_value_plan', 0.0),
                'opening_stock_shops_qty_plan': data.get('opening_stock_shops_qty_plan', 0),
                'opening_stock_shops_value_plan': data.get('opening_stock_shops_value_plan', 0.0),
                'opening_stock_total_qty_plan': data.get('opening_stock_total_qty_plan', 0),
                'opening_stock_total_value_plan': data.get('opening_stock_total_value_plan', 0.0),

                # Actual metrics
                'actual_prospects': data['actual_prospects'],
                'actual_followups': data['actual_followups'],
                'actual_site_visits': data['actual_site_visits'],
                'actual_office_visits': data['actual_office_visits'],
                'actual_total_visits': data['actual_total_visits'],
                'actual_unit_reservations': data['actual_unit_reservations'],
                'actual_deals_closed': data['actual_deals_closed'],
                'actual_cash_collected': data['actual_cash_collected'],
                'actual_total_deal_value': data['actual_total_deal_value'],
                'actual_conversion': data['actual_conversion'],
                'actual_iar': data['actual_iar'],
                'actual_opening_stock_residence_qty': data.get('actual_opening_stock_residence_qty', 0),
                'actual_opening_stock_residence_value': data.get('actual_opening_stock_residence_value', 0.0),
                'actual_opening_stock_shops_qty': data.get('actual_opening_stock_shops_qty', 0),
                'actual_opening_stock_shops_value': data.get('actual_opening_stock_shops_value', 0.0),
                'actual_opening_stock_total_qty': data.get('actual_opening_stock_total_qty', 0),
                'actual_opening_stock_total_value': data.get('actual_opening_stock_total_value', 0.0),
                'actual_opening_stock_residence_qty': data.get('actual_opening_stock_residence_qty', 0),
                'actual_opening_stock_residence_value': data.get('actual_opening_stock_residence_value', 0.0),
                'actual_opening_stock_shops_qty': data.get('actual_opening_stock_shops_qty', 0),
                'actual_opening_stock_shops_value': data.get('actual_opening_stock_shops_value', 0.0),
                'actual_opening_stock_total_qty': data.get('actual_opening_stock_total_qty', 0),
                'actual_opening_stock_total_value': data.get('actual_opening_stock_total_value', 0.0),

                # Previous metrics
                'previous_prospects': data['previous_prospects'],
                'previous_followups': data['previous_followups'],
                'previous_site_visits': data['previous_site_visits'],
                'previous_office_visits': data['previous_office_visits'],
                'previous_total_visits': data['previous_total_visits'],
                'previous_unit_reservations': data['previous_unit_reservations'],
                'previous_deals_closed': data['previous_deals_closed'],
                'previous_cash_collected': data['previous_cash_collected'],
                'previous_total_deal_value': data['previous_total_deal_value'],

                # Remarks
                'prospect_remark': data['prospect_remark'],
                'followup_remark': data['followup_remark'],
                'site_visit_remark': data['site_visit_remark'],
                'office_visit_remark': data['office_visit_remark'],
                'total_visit_remark': data['total_visit_remark'],
                'unit_reservation_remark': data['unit_reservation_remark'],
                'deals_closed_remark': data['deals_closed_remark'],
                'cash_collected_remark': data['cash_collected_remark'],
                'total_deal_value_remark': data['total_deal_value_remark'],
                'conversion_remark': data['conversion_remark'],
                'iar_remark': data['iar_remark'],
            })

            return virtual_plan.id

        # Helper methods for counting metrics
        def _get_lead_count(self, start_date, end_date, user_ids, lead_type):
            """Get lead count by type"""
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            query = """
                    SELECT COUNT(*)
                    FROM temer_lead
                    WHERE create_date >= %s
                      AND create_date <= %s
                      AND user_id IN %s \
                    """

            if lead_type == 'prospect':
                query += " AND state IN ('prospect', 'reservation', 'won', 'new_lead')"
            else:  # follow_up
                query += " AND state NOT IN ('prospect', 'reservation', 'won', 'new_lead')"

            self.env.cr.execute(query, (start_datetime, end_datetime, tuple(user_ids)))
            result = self.env.cr.fetchone()
            return result[0] if result else 0

        def _get_activity_count(self, start_date, end_date, user_ids, activity_type):
            """Get activity count by type"""
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            query = """
                    SELECT COUNT(*)
                    FROM temer_lead_activity_wizard
                    WHERE create_date >= %s
                      AND create_date <= %s
                      AND activity_type = %s
                      AND lead_id IN (SELECT id FROM temer_lead WHERE user_id IN %s) \
                    """

            self.env.cr.execute(query, (start_datetime, end_datetime, activity_type, tuple(user_ids)))
            result = self.env.cr.fetchone()
            return result[0] if result else 0

        def _get_reservation_count(self, start_date, end_date, user_ids):
            """Get reservation count"""
            query = """
                SELECT COUNT(DISTINCT pr.id)
                FROM property_reservation pr
                JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                WHERE DATE(pr.create_date) BETWEEN %s AND %s
                  AND pr.status IN ('reserved', 'requested', 'pending_sales')
                  AND prc.reservation_type IN ('quick', 'regular')
                  AND pr.salesperson_ids IN %s
            """
            self.env.cr.execute(query, (start_date, end_date, tuple(user_ids)))
            result = self.env.cr.fetchone()
            return result[0] if result else 0

        def _get_deal_count(self, start_date, end_date, user_ids):
            """Get deal count"""
            query = """
                SELECT COUNT(*)
                FROM property_sale ps
                WHERE DATE(ps.create_date) BETWEEN %s AND %s
                  AND ps.state = 'confirm'
                  AND ps.create_uid IN %s
            """
            self.env.cr.execute(query, (start_date, end_date, tuple(user_ids)))
            result = self.env.cr.fetchone()
            return result[0] if result else 0

    class SupervisorPlanReportAction(models.TransientModel):
        _name = 'supervisor.plan.report.action'
        _description = 'Supervisor Plan Report Action'

        supervisor_id = fields.Many2one('res.users', string='Supervisor', required=True,
                                        domain=lambda self: self._get_supervisor_domain())
        start_date = fields.Date(string='From Date', required=True, default=fields.Date.today())
        end_date = fields.Date(string='To Date', required=True, default=fields.Date.today())

        def _get_supervisor_domain(self):
            """Get domain to show only supervisors"""
            try:
                if 'property.sales.supervisor' in self.env:
                    supervisors = self.env['property.sales.supervisor'].search([])
                    supervisor_user_ids = supervisors.mapped('name.id')
                    return [('id', 'in', supervisor_user_ids)]
            except Exception as e:
                _logger.warning(f"Error getting supervisor domain: {e}")
            return []

        def action_view_supervisor_report(self):
            """Generate aggregated supervisor report"""
            self.ensure_one()

            # Get all salespersons under this supervisor
            salesperson_mappings = self.env['property.salesperson.mapping'].search([
                ('supervisor_id.name', '=', self.supervisor_id.id)
            ])
            salesperson_ids = salesperson_mappings.mapped('user_id.id')

            # Get the supervisor's sales plans
            plans = self.env['sales.plan'].search([
                ('supervisor_id', '=', self.supervisor_id.id),
                ('start_date', '<=', self.end_date),
                ('end_date', '>=', self.start_date),
                ('state', '=', 'completed')
            ])

            # Calculate aggregated metrics
            aggregated_data = self._calculate_supervisor_aggregated_metrics(plans, salesperson_ids)

            # Create a virtual plan for display
            virtual_plan_id = self._create_virtual_supervisor_plan(aggregated_data)

            # Open the report view
            return {
                'type': 'ir.actions.act_window',
                'name': f'Supervisor Report - {self.supervisor_id.name} ({self.start_date} to {self.end_date})',
                'res_model': 'sales.plan',
                'res_id': virtual_plan_id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {'form_view_ref': 'sales_plan_module.view_sales_plan_report_form'},
            }

        def _calculate_supervisor_aggregated_metrics(self, plans, salesperson_ids):
            """Calculate aggregated metrics for supervisor and their salespersons"""

            # Get supervisor's wing
            supervisor_record = self.env['property.sales.supervisor'].search([
                ('name', '=', self.supervisor_id.id)
            ], limit=1)

            wing_id = supervisor_record.sales_team_id.wing_id.id if supervisor_record and supervisor_record.sales_team_id else False

            aggregated = {
                'name': f'Supervisor Aggregated Report - {self.supervisor_id.name}',
                'supervisor_id': self.supervisor_id.id,
                'wing_id': wing_id,

                # Plan totals (from supervisor's plans)
                'prospect_plan': sum(plans.mapped('prospect_plan')) if plans else 0,
                'followup_plan': sum(plans.mapped('followup_plan')) if plans else 0,
                'site_visit_plan': sum(plans.mapped('site_visit_plan')) if plans else 0,
                'office_visit_plan': sum(plans.mapped('office_visit_plan')) if plans else 0,
                'total_visit_plan': sum(plans.mapped('total_visit_plan')) if plans else 0,
                'unit_reservation_plan': sum(plans.mapped('unit_reservation_plan')) if plans else 0,
                'deals_closed_plan': sum(plans.mapped('deals_closed_plan')) if plans else 0,
                'cash_collected_plan': sum(plans.mapped('cash_collected_plan')) if plans else 0,
                'total_deal_value_plan': sum(plans.mapped('total_deal_value_plan')) if plans else 0,
                'conversion_plan': plans and sum(plans.mapped('conversion_plan')) / len(plans) or 0,
                'iar_plan': plans and sum(plans.mapped('iar_plan')) / len(plans) or 0,
                'opening_stock_residence_qty_plan': sum(plans.mapped('opening_stock_residence_qty_plan')) if plans else 0,
                'opening_stock_residence_value_plan': sum(plans.mapped('opening_stock_residence_value_plan')) if plans else 0,
                'opening_stock_shops_qty_plan': sum(plans.mapped('opening_stock_shops_qty_plan')) if plans else 0,
                'opening_stock_shops_value_plan': sum(plans.mapped('opening_stock_shops_value_plan')) if plans else 0,
                'opening_stock_total_qty_plan': sum(plans.mapped('opening_stock_total_qty_plan')) if plans else 0,
                'opening_stock_total_value_plan': sum(plans.mapped('opening_stock_total_value_plan')) if plans else 0,

                # Actual totals (calculated from supervisor + all their salespersons)
                'actual_prospects': 0,
                'actual_followups': 0,
                'actual_site_visits': 0,
                'actual_office_visits': 0,
                'actual_total_visits': 0,
                'actual_unit_reservations': 0,
                'actual_deals_closed': 0,
                'actual_cash_collected': 0.0,
                'actual_total_deal_value': 0.0,
                'actual_conversion': 0.0,
                'actual_iar': 0.0,
                'actual_opening_stock_residence_qty': 0,
                'actual_opening_stock_residence_value': 0.0,
                'actual_opening_stock_shops_qty': 0,
                'actual_opening_stock_shops_value': 0.0,
                'actual_opening_stock_total_qty': 0,
                'actual_opening_stock_total_value': 0.0,

                # Previous week totals
                'previous_prospects': 0,
                'previous_followups': 0,
                'previous_site_visits': 0,
                'previous_office_visits': 0,
                'previous_total_visits': 0,
                'previous_unit_reservations': 0,
                'previous_deals_closed': 0,
                'previous_cash_collected': 0.0,
                'previous_total_deal_value': 0.0,

                # Remarks
                'prospect_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'followup_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'site_visit_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'office_visit_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'total_visit_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'unit_reservation_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'deals_closed_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'cash_collected_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'total_deal_value_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'conversion_remark': f'Aggregated Report for {self.supervisor_id.name}',
                'iar_remark': f'Aggregated Report for {self.supervisor_id.name}',
            }

            # Calculate actual metrics for supervisor + all their salespersons
            all_user_ids = [self.supervisor_id.id] + salesperson_ids

            if all_user_ids:
                # Reuse the counting methods from WingPlanReportAction
                wing_action = self.env['wing.plan.report.action']

                aggregated['actual_prospects'] = wing_action._get_lead_count(self.start_date, self.end_date,
                                                                             all_user_ids, 'prospect')
                aggregated['actual_followups'] = wing_action._get_lead_count(self.start_date, self.end_date,
                                                                             all_user_ids, 'follow_up')
                aggregated['actual_site_visits'] = wing_action._get_activity_count(self.start_date, self.end_date,
                                                                                   all_user_ids, 'site_visit')
                aggregated['actual_office_visits'] = wing_action._get_activity_count(self.start_date, self.end_date,
                                                                                     all_user_ids, 'office_visit')
                aggregated['actual_total_visits'] = aggregated['actual_site_visits'] + aggregated[
                    'actual_office_visits']
                aggregated['actual_unit_reservations'] = wing_action._get_reservation_count(self.start_date,
                                                                                            self.end_date, all_user_ids)
                aggregated['actual_deals_closed'] = wing_action._get_deal_count(self.start_date, self.end_date,
                                                                                all_user_ids)
                aggregated['actual_cash_collected'] = self.env['sales.plan']._get_cash_collected_amount(
                    self.start_date, self.end_date, all_user_ids
                )
                aggregated['actual_total_deal_value'] = self.env['sales.plan']._get_total_deal_value(
                    self.start_date, self.end_date, all_user_ids
                )

                opening_stock = self.env['sales.plan']._get_opening_stock_values(self.start_date)
                aggregated['actual_opening_stock_residence_qty'] = opening_stock['residence_qty']
                aggregated['actual_opening_stock_residence_value'] = opening_stock['residence_value']
                aggregated['actual_opening_stock_shops_qty'] = opening_stock['shops_qty']
                aggregated['actual_opening_stock_shops_value'] = opening_stock['shops_value']
                aggregated['actual_opening_stock_total_qty'] = opening_stock['residence_qty'] + opening_stock['shops_qty']
                aggregated['actual_opening_stock_total_value'] = opening_stock['residence_value'] + opening_stock['shops_value']

                # Calculate previous week metrics
                prev_start = self.start_date - timedelta(days=7)
                prev_end = self.start_date - timedelta(days=1)

                aggregated['previous_prospects'] = wing_action._get_lead_count(prev_start, prev_end, all_user_ids,
                                                                               'prospect')
                aggregated['previous_followups'] = wing_action._get_lead_count(prev_start, prev_end, all_user_ids,
                                                                               'follow_up')
                aggregated['previous_site_visits'] = wing_action._get_activity_count(prev_start, prev_end, all_user_ids,
                                                                                     'site_visit')
                aggregated['previous_office_visits'] = wing_action._get_activity_count(prev_start, prev_end,
                                                                                       all_user_ids, 'office_visit')
                aggregated['previous_total_visits'] = aggregated['previous_site_visits'] + aggregated[
                    'previous_office_visits']
                aggregated['previous_unit_reservations'] = wing_action._get_reservation_count(prev_start, prev_end,
                                                                                              all_user_ids)
                aggregated['previous_deals_closed'] = wing_action._get_deal_count(prev_start, prev_end, all_user_ids)
                aggregated['previous_cash_collected'] = self.env['sales.plan']._get_cash_collected_amount(
                    prev_start, prev_end, all_user_ids
                )
                aggregated['previous_total_deal_value'] = self.env['sales.plan']._get_total_deal_value(
                    prev_start, prev_end, all_user_ids
                )

                # Calculate conversion (ratio, not percent)
                if aggregated['actual_prospects'] > 0:
                    aggregated['actual_conversion'] = (aggregated['actual_deals_closed'] / aggregated['actual_prospects'])
                if aggregated['actual_opening_stock_total_value'] > 0:
                    aggregated['actual_iar'] = (aggregated['actual_total_deal_value'] / aggregated[
                        'actual_opening_stock_total_value']) * 100

            return aggregated

        def _create_virtual_supervisor_plan(self, data):
            """Create a temporary virtual plan for display"""
            virtual_plan = self.env['sales.plan'].create({
                'name': data['name'],
                'plan_type': 'monthly',
                'start_date': self.start_date,
                'end_date': self.end_date,
                'supervisor_id': data['supervisor_id'],
                'wing_id': data['wing_id'],
                'state': 'completed',

                # Plan targets
                'prospect_plan': data['prospect_plan'],
                'followup_plan': data['followup_plan'],
                'site_visit_plan': data['site_visit_plan'],
                'office_visit_plan': data['office_visit_plan'],
                'total_visit_plan': data['total_visit_plan'],
                'unit_reservation_plan': data['unit_reservation_plan'],
                'deals_closed_plan': data['deals_closed_plan'],
                'cash_collected_plan': data['cash_collected_plan'],
                'total_deal_value_plan': data['total_deal_value_plan'],
                'conversion_plan': data['conversion_plan'],
                'iar_plan': data['iar_plan'],

                # Actual metrics
                'actual_prospects': data['actual_prospects'],
                'actual_followups': data['actual_followups'],
                'actual_site_visits': data['actual_site_visits'],
                'actual_office_visits': data['actual_office_visits'],
                'actual_total_visits': data['actual_total_visits'],
                'actual_unit_reservations': data['actual_unit_reservations'],
                'actual_deals_closed': data['actual_deals_closed'],
                'actual_cash_collected': data['actual_cash_collected'],
                'actual_total_deal_value': data['actual_total_deal_value'],
                'actual_conversion': data['actual_conversion'],
                'actual_iar': data['actual_iar'],

                # Previous metrics
                'previous_prospects': data['previous_prospects'],
                'previous_followups': data['previous_followups'],
                'previous_site_visits': data['previous_site_visits'],
                'previous_office_visits': data['previous_office_visits'],
                'previous_total_visits': data['previous_total_visits'],
                'previous_unit_reservations': data['previous_unit_reservations'],
                'previous_deals_closed': data['previous_deals_closed'],
                'previous_cash_collected': data['previous_cash_collected'],
                'previous_total_deal_value': data['previous_total_deal_value'],

                # Remarks
                'prospect_remark': data['prospect_remark'],
                'followup_remark': data['followup_remark'],
                'site_visit_remark': data['site_visit_remark'],
                'office_visit_remark': data['office_visit_remark'],
                'total_visit_remark': data['total_visit_remark'],
                'unit_reservation_remark': data['unit_reservation_remark'],
                'deals_closed_remark': data['deals_closed_remark'],
                'cash_collected_remark': data['cash_collected_remark'],
                'total_deal_value_remark': data['total_deal_value_remark'],
                'conversion_remark': data['conversion_remark'],
                'iar_remark': data['iar_remark'],
            })

            return virtual_plan.id
