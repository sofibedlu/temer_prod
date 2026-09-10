# -*- coding: utf-8 -*-
"""
Temer Lead Analysis Report Wizard
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)

class TemerLeadAnalysisWizard(models.TransientModel):
    _name = "temer.lead.analysis.wizard"
    _description = "Temer Lead Analysis Report Wizard"

    date_filter = fields.Selection([
        ('custom', 'Custom'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
    ], string="Date Filter", default='custom')

    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    
    report_by = fields.Selection([
        ('wing', 'Wing'),
        ('supervisor', 'Supervisor'),
        ('salesperson', 'Salesperson'),
    ], string='Report By', required=True, default='wing')
    
    wing_id = fields.Selection(
        selection='_get_wing_selection',
        string='Wing',
        required=True,
    )
    
    include_crm_leads = fields.Boolean(
        string='Include CRM Leads',
        default=False,
        help="Combine data from both Temer Leads and CRM Leads"
    )

    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        today = fields.Date.context_today(self)
        if self.date_filter == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.date_from = start
            self.date_to = end
        elif self.date_filter == 'this_month':
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            self.date_from = start
            self.date_to = end

    @api.model
    def _get_wing_selection(self):
        """
        Dynamically show wings based on user group access.
        """
        user = self.env.user
        wings = []
        # Always add No Wing if allowed
        if user.has_group('custom_report_wizard.group_no_wing_access'):
            wings.append(('no_wing', 'No Wing'))
        # Fetch from DB
        self.env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
        for w_id, w_name in self.env.cr.fetchall():
            name_lower = w_name.strip().lower()
            # Match against lowercase strings!
            if name_lower == "team - ajwa" and user.has_group('custom_report_wizard.group_team_ajwa_access'):
                wings.append((str(w_id), w_name))
            if name_lower == "team - taj" and user.has_group('custom_report_wizard.group_team_taj_access'):
                wings.append((str(w_id), w_name))
            if name_lower == "team - raha" and user.has_group('custom_report_wizard.group_team_Raha_access'):
                wings.append((str(w_id), w_name))
        return wings

    def _validate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("`From` date must be before `To` date."))
        if not self.wing_id:
            raise UserError(_("Please select a Wing to view its analysis."))

    def _fetch_temer_leads_data(self):
        """Fetch data from temer.lead model using pure ORM approach"""
        self.ensure_one()
        
        # Build domain
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ]
        
        # Add wing filter
        if self.wing_id:
            if self.wing_id == 'no_wing':
                domain.append(('computed_wing_id', '=', False))
            else:
                domain.append(('computed_wing_id', '=', int(self.wing_id)))
        
        # Get all leads in the date range
        leads = self.env['temer.lead'].search(domain)
        
        _logger.info(f"Found {len(leads)} temer leads for analysis")
        
        # Group data
        grouped_data = {}
        
        for lead in leads:
            try:
                # Get wing information
                wing_name = 'No Wing'
                wing_manager_name = 'No Manager'
                if lead.computed_wing_id:
                    wing_name = lead.computed_wing_id.name or 'Wing (No Name)'
                    if lead.computed_wing_id.manager_id and lead.computed_wing_id.manager_id.partner_id:
                        wing_manager_name = lead.computed_wing_id.manager_id.partner_id.name or 'Manager (No Name)'
                
                # Get supervisor information - FIXED
                supervisor_name = 'No Supervisor'
                if lead.computed_supervisor_id:
                    # The supervisor name is stored in the related user's partner name
                    if lead.computed_supervisor_id.name and lead.computed_supervisor_id.name.partner_id:
                        supervisor_name = lead.computed_supervisor_id.name.partner_id.name or 'Supervisor (No Name)'
                    else:
                        supervisor_name = lead.computed_supervisor_id.name or 'Supervisor (No Name)'
                
                # Get salesperson information
                sales_person = 'No Salesperson'
                if lead.user_id and lead.user_id.partner_id:
                    sales_person = lead.user_id.partner_id.name or 'Salesperson (No Name)'
                
                # Create grouping key based on report_by selection
                if self.report_by == 'wing':
                    key = (wing_name, wing_manager_name)
                elif self.report_by == 'supervisor':
                    key = (wing_name, wing_manager_name, supervisor_name)
                else:  # salesperson
                    key = (wing_name, wing_manager_name, supervisor_name, sales_person)
                
                # Initialize group if not exists
                if key not in grouped_data:
                    grouped_data[key] = {
                        'wing_name': wing_name,
                        'wing_manager_name': wing_manager_name,
                        'supervisor_name': supervisor_name if self.report_by in ['supervisor', 'salesperson'] else '',
                        'sales_person': sales_person if self.report_by == 'salesperson' else '',
                        'prospect': 0,
                        'follow_up': 0,
                        'reservation_count': 0,
                        'sold_reservation_count': 0,
                        'expired': 0,
                        'lost': 0,
                        'total': 0,
                        'total_activities': 0,
                    }
                
                # Update counts
                group = grouped_data[key]
                group['total'] += 1
                
                # Count by state
                if lead.state == 'prospect':
                    group['prospect'] += 1
                elif lead.state == 'follow_up':
                    group['follow_up'] += 1
                elif lead.state == 'reservation':
                    group['reservation_count'] += 1
                elif lead.state == 'won':
                    group['sold_reservation_count'] += 1
                elif lead.state == 'lost':
                    group['lost'] += 1
                elif lead.state == 'expired':
                    group['expired'] += 1
                
                # Count activities
                group['total_activities'] += len(lead.followup_line_ids)
                
            except Exception as e:
                _logger.error(f"Error processing lead {lead.id}: {str(e)}")
                continue
        
        # Convert to the format expected by the report
        rows = []
        for key, data in grouped_data.items():
            rows.append((
                data['wing_name'],
                data['wing_manager_name'],
                data['supervisor_name'],
                data['sales_person'],
                data['prospect'],
                data['follow_up'],
                data['reservation_count'],
                data['sold_reservation_count'],
                0,  # requested_reservation_count
                0,  # expired_reservation_count
                0,  # canceled_reservation_count
                data['expired'],
                data['lost'],
                0,  # current_reservation
                data['total'],
                data['total_activities'],
                '✅ OK'
            ))
        
        _logger.info(f"Processed {len(rows)} groups for temer leads report")
        return rows

    def _fetch_crm_leads_data(self):
        """Fetch data from crm.lead model"""
        self.ensure_one()
        
        # Wing filter construction
        wing_condition = ""
        wing_param = None
        if self.wing_id:
            if self.wing_id == 'no_wing':
                wing_condition = " AND cl.wing_id IS NULL"
            else:
                wing_condition = " AND cl.wing_id = %s"
                wing_param = int(self.wing_id)

        date_from = self.date_from
        date_to = self.date_to

        params = [date_from, date_to]
        if wing_param is not None:
            params.append(wing_param)

        query = f"""
            WITH crm_lead_data AS (
                SELECT 
                    cl.id as lead_id,
                    cl.create_date,
                    cl.stage_id,
                    cs.name::jsonb->>'en_US' as stage_name,
                    cl.user_id,
                    COALESCE(up.name, 'No Salesperson') as sales_person,
                    cl.supervisor_id,
                    COALESCE(ps.name, 'No Supervisor') as supervisor_name,
                    COALESCE(psw.name, 'No Wing') as wing_name,
                    COALESCE(rp_wing.name, '') as wing_manager_name
                FROM crm_lead cl
                LEFT JOIN res_users u ON cl.user_id = u.id
                LEFT JOIN res_partner up ON u.partner_id = up.id
                LEFT JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                LEFT JOIN res_users ru_sup ON pss.name = ru_sup.id
                LEFT JOIN res_partner ps ON ru_sup.partner_id = ps.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                LEFT JOIN crm_stage cs ON cl.stage_id = cs.id
                WHERE cl.create_date BETWEEN %s AND %s
                {wing_condition}
            ),
            stage_counts AS (
                SELECT
                    wing_name,
                    wing_manager_name,
                    supervisor_name,
                    sales_person,
                    COUNT(CASE WHEN stage_name LIKE '%%Prospect%%' OR stage_name LIKE '%%New%%' THEN 1 END) as prospect,
                    COUNT(CASE WHEN stage_name LIKE '%%Qualified%%' OR stage_name LIKE '%%Follow%%' THEN 1 END) as follow_up,
                    COUNT(CASE WHEN stage_name LIKE '%%Reservation%%' THEN 1 END) as reservation_count,
                    COUNT(CASE WHEN stage_name LIKE '%%Won%%' OR stage_name LIKE '%%Sold%%' THEN 1 END) as sold_reservation_count,
                    COUNT(CASE WHEN stage_name LIKE '%%Lost%%' THEN 1 END) as lost,
                    COUNT(CASE WHEN stage_name LIKE '%%Expired%%' THEN 1 END) as expired,
                    COUNT(*) as total
                FROM crm_lead_data
                GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
            )
            SELECT 
                wing_name,
                wing_manager_name,
                supervisor_name,
                sales_person,
                prospect,
                follow_up,
                reservation_count,
                sold_reservation_count,
                0 as requested_reservation_count,
                0 as expired_reservation_count,
                0 as canceled_reservation_count,
                expired,
                lost,
                0 as current_reservation,
                total,
                0 as total_activities,
                '✅ OK' as data_flag
            FROM stage_counts
            ORDER BY wing_name, wing_manager_name
        """

        self.env.cr.execute(query, tuple(params))
        return self.env.cr.fetchall()

    def _prepare_report_data(self):
        """Prepare report data for both temer leads and optionally crm leads"""
        self._validate()
        
        # Fetch temer leads data
        temer_rows = self._fetch_temer_leads_data()
        
        # Fetch CRM leads data if requested
        crm_rows = []
        if self.include_crm_leads:
            crm_rows = self._fetch_crm_leads_data()
        
        # Combine data
        all_rows = temer_rows + crm_rows
        
        # Group and aggregate data
        rows = []
        totals = {
            "prospect": 0,
            "follow_up": 0,
            "reservation_count": 0,
            "sold_reservation_count": 0,
            "expired": 0,
            "lost": 0,
            "current_reservation": 0,
            "total": 0,
            "total_activities": 0,
        }
        
        all_fields = ['wing_name', 'wing_manager_name', 'supervisor_name', 'sales_person']
        if self.report_by == 'wing':
            group_fields = ['wing_name', 'wing_manager_name']
        elif self.report_by == 'supervisor':
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name']
        else:
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name', 'sales_person']

        grouped = {}
        for row in all_rows:
            row_dict = {
                "wing_name": row[0] or '',
                "wing_manager_name": row[1] or '',
                "supervisor_name": row[2] or '',
                "sales_person": row[3] or '',
                "prospect": int(row[4] or 0),
                "follow_up": int(row[5] or 0),
                "reservation_count": int(row[6] or 0),
                "sold_reservation_count": int(row[7] or 0),
                "requested_reservation_count": int(row[8] or 0),
                "expired_reservation_count": int(row[9] or 0),
                "canceled_reservation_count": int(row[10] or 0),
                "expired": int(row[11] or 0),
                "lost": int(row[12] or 0),
                "current_reservation": int(row[13] or 0),
                "total": int(row[14] or 0),
                "total_activities": int(row[15] or 0),
                "data_flag": row[16],
            }
            
            # Update totals
            for key in totals:
                if key in row_dict:
                    totals[key] += row_dict[key]
            
            # Group data
            key = tuple(row_dict[field] for field in group_fields)
            if key in grouped:
                for field in ['prospect', 'follow_up', 'reservation_count', 'sold_reservation_count', 
                            'expired', 'lost', 'total', 'total_activities']:
                    grouped[key][field] += row_dict[field]
            else:
                grouped[key] = {f: row_dict[f] for f in all_fields}
                grouped[key].update({
                    "prospect": row_dict["prospect"],
                    "follow_up": row_dict["follow_up"],
                    "reservation_count": row_dict["reservation_count"],
                    "sold_reservation_count": row_dict["sold_reservation_count"],
                    "expired": row_dict["expired"],
                    "lost": row_dict["lost"],
                    "total": row_dict["total"],
                    "total_activities": row_dict["total_activities"],
                    "data_flag": row_dict["data_flag"],
                })
                for unused in set(all_fields) - set(group_fields):
                    if unused not in grouped[key]:
                        grouped[key][unused] = ''
        
        rows = list(grouped.values())

        wing_dict = dict(self._get_wing_selection())
        selected_wing_name = wing_dict.get(self.wing_id, '') if self.wing_id else ''

        data = {
            "rows": rows,
            "totals": totals,
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "report_by": self.report_by,
            "wing_name": selected_wing_name,
            "include_crm_leads": self.include_crm_leads,
        }
        return data
    
    def _get_report_values(self, docids, data=None):
        """
        Override to prepare report data when called via URL
        This method is called by the report engine
        """
        # Get the wizard record
        docs = self.browse(docids)
        # Prepare the report data using the existing method
        report_data = docs._prepare_report_data()
        return report_data

    def action_print(self):
        """Generate PDF for download"""
        data = self._prepare_report_data()
        return self.env.ref('custom_report_wizard.temer_lead_analysis_pdf').report_action(self, data=data)
    
    def action_preview(self):
        """Generate PDF for browser preview in new tab"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/custom_report_wizard.temer_lead_analysis_pdf/{self.id}',
            'target': 'new',
        }
    # def action_preview(self):
    #     """Generate HTML for browser preview"""
    #     data = self._prepare_report_data()
    #     return self.env.ref('custom_report_wizard.temer_lead_analysis_html').report_action(self, data=data)