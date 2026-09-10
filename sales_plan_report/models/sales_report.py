# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import date, datetime

_logger = logging.getLogger(__name__)


class SalesReport(models.TransientModel):
    _name = 'sales.report'
    _description = 'Sales Performance Report'

    name = fields.Char('Report Name', default='Sales Report')

    # Selection fields - will be set from context
    report_type = fields.Selection([
        ('wing', 'Wing Report'),
        ('supervisor', 'Supervisor Report')
    ], string='Report Type', required=True, default='wing', readonly=True)

    wing_id = fields.Many2one('property.sales.wing', string='Wing')
    supervisor_id = fields.Many2one('property.sales.supervisor', string='Supervisor')

    date_from = fields.Date('From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date('To Date', required=True, default=fields.Date.context_today)

    # Report Results - Will be calculated
    # Prospects
    plan_prospects = fields.Integer('Plan Prospects', default=0)
    actual_prospects = fields.Integer('Actual Prospects', default=0)
    actual_this_week_prospects = fields.Integer('Actual This Week Prospects', default=0)  # Monday to today
    actual_previous_week_prospects = fields.Integer('Actual Previous Week Prospects', default=0)
    diff_prospects = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences', store=False)
    diff_week_prospects = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_prospects = fields.Float('%', compute='_compute_percentages')

    # Follow-ups
    plan_follow_ups = fields.Integer('Plan Follow-ups', default=0)
    actual_follow_ups = fields.Integer('Actual Follow-ups', default=0)
    actual_this_week_follow_ups = fields.Integer('Actual This Week Follow-ups', default=0)
    actual_previous_week_follow_ups = fields.Integer('Actual Previous Week Follow-ups', default=0)
    diff_follow_ups = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_follow_ups = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_follow_ups = fields.Float('%', compute='_compute_percentages')

    # Site Visits
    plan_site_visits = fields.Integer('Plan Site Visits', default=0)
    actual_site_visits = fields.Integer('Actual Site Visits', default=0)
    actual_this_week_site_visits = fields.Integer('Actual This Week Site Visits', default=0)
    actual_previous_week_site_visits = fields.Integer('Actual Previous Week Site Visits', default=0)
    diff_site_visits = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_site_visits = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_site_visits = fields.Float('%', compute='_compute_percentages')

    # Office Visits
    plan_office_visits = fields.Integer('Plan Office Visits', default=0)
    actual_office_visits = fields.Integer('Actual Office Visits', default=0)
    actual_this_week_office_visits = fields.Integer('Actual This Week Office Visits', default=0)
    actual_previous_week_office_visits = fields.Integer('Actual Previous Week Office Visits', default=0)
    diff_office_visits = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_office_visits = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_office_visits = fields.Float('%', compute='_compute_percentages')

    # Total Visits
    plan_total_visits = fields.Integer('Plan Total Visits', compute='_compute_total_visits')
    actual_total_visits = fields.Integer('Actual Total Visits', compute='_compute_total_visits')
    actual_this_week_total_visits = fields.Integer('Actual This Week Total Visits', compute='_compute_this_week_total_visits')
    actual_previous_week_total_visits = fields.Integer('Actual Previous Week Total Visits', compute='_compute_total_visits')
    diff_total_visits = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_total_visits = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_total_visits = fields.Float('%', compute='_compute_percentages')

    # Unit Reservations
    plan_unit_reservations = fields.Integer('Plan Unit Reservations', default=0)
    actual_unit_reservations = fields.Integer('Actual Unit Reservations', default=0)
    actual_this_week_unit_reservations = fields.Integer('Actual This Week Unit Reservations', default=0)
    actual_previous_week_unit_reservations = fields.Integer('Actual Previous Week Unit Reservations', default=0)
    diff_unit_reservations = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_unit_reservations = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_unit_reservations = fields.Float('%', compute='_compute_percentages')

    # Deals Closed
    plan_deals_closed = fields.Integer('Plan Deals Closed', default=0)
    actual_deals_closed = fields.Integer('Actual Deals Closed', default=0)
    actual_this_week_deals_closed = fields.Integer('Actual This Week Deals Closed', default=0)
    actual_previous_week_deals_closed = fields.Integer('Actual Previous Week Deals Closed', default=0)
    diff_deals_closed = fields.Integer('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_deals_closed = fields.Integer('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_deals_closed = fields.Float('%', compute='_compute_percentages')

    # Conversion Rate
    plan_conversion_rate = fields.Float('Plan Conversion Rate', default=0.0)
    conversion_rate = fields.Float('Conversion Rate', compute='_compute_conversion_rate')
    actual_previous_week_conversion_rate = fields.Float('Actual Previous Week Conversion Rate', compute='_compute_previous_week_conversion_rate')
    diff_conversion_rate = fields.Float('Difference (Actual - Plan) Conversion', compute='_compute_rate_differences')
    diff_week_conversion_rate = fields.Float('Difference (This week - Previous week) Conversion', compute='_compute_rate_differences')
    percent_conversion_rate = fields.Float('% Conversion', compute='_compute_rate_percentages')
    
    # Cash Collected
    plan_cash_collected = fields.Float('Plan Cash Collected (Birr)', default=0.0)
    actual_cash_collected = fields.Float('Actual Cash Collected (Birr)', default=0.0)
    actual_this_week_cash_collected = fields.Float('Actual This Week Cash Collected (Birr)', default=0.0)
    actual_previous_week_cash_collected = fields.Float('Actual Previous Week Cash Collected (Birr)', default=0.0)
    diff_cash_collected = fields.Float('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_cash_collected = fields.Float('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_cash_collected = fields.Float('%', compute='_compute_percentages')
    
    # Total Deal Value
    plan_total_deal_value = fields.Float('Plan Total Deal Value (Birr)', default=0.0)
    actual_total_deal_value = fields.Float('Actual Total Deal Value (Birr)', default=0.0)
    actual_this_week_total_deal_value = fields.Float('Actual This Week Total Deal Value (Birr)', default=0.0)
    actual_previous_week_total_deal_value = fields.Float('Actual Previous Week Total Deal Value (Birr)', default=0.0)
    diff_total_deal_value = fields.Float('Difference (Actual - Plan)', compute='_compute_differences')
    diff_week_total_deal_value = fields.Float('Difference (This week - Previous week)', compute='_compute_week_differences')
    percent_total_deal_value = fields.Float('%', compute='_compute_percentages')
    
    # IAR (Inventory Absorption Rate)
    plan_iar_rate = fields.Float('Plan IAR %', default=0.0)
    iar_rate = fields.Float('IAR (sales/opening stock)', compute='_compute_iar_rate', default=0.0)
    actual_previous_week_iar_rate = fields.Float('Actual Previous Week IAR %', compute='_compute_previous_week_iar_rate')
    diff_iar_rate = fields.Float('Difference (Actual - Plan) IAR', compute='_compute_rate_differences')
    diff_week_iar_rate = fields.Float('Difference (This week - Previous week) IAR', compute='_compute_rate_differences')
    percent_iar_rate = fields.Float('% IAR', compute='_compute_rate_percentages')
    
    # Opening Stock
    opening_stock_residence_qty = fields.Integer('Opening Stock Residence QTY', default=0)
    opening_stock_residence_value = fields.Float('Opening Stock Residence Value (Birr)', default=0.0)
    opening_stock_shops_qty = fields.Integer('Opening Stock Shops QTY', default=0)
    opening_stock_shops_value = fields.Float('Opening Stock Shops Value (Birr)', default=0.0)
    opening_stock_total_qty = fields.Integer('Opening Stock Total QTY', compute='_compute_opening_stock_total')
    opening_stock_total_value = fields.Float('Opening Stock Total Value (Birr)', compute='_compute_opening_stock_total')

    # Opening Stock Plan
    plan_opening_stock_residence_qty = fields.Integer('Plan Opening Stock Residence QTY', default=0)
    plan_opening_stock_residence_value = fields.Float('Plan Opening Stock Residence Value (Birr)', default=0.0)
    plan_opening_stock_shops_qty = fields.Integer('Plan Opening Stock Shops QTY', default=0)
    plan_opening_stock_shops_value = fields.Float('Plan Opening Stock Shops Value (Birr)', default=0.0)
    plan_opening_stock_total_qty = fields.Integer('Plan Opening Stock Total QTY', compute='_compute_plan_opening_stock_total')
    plan_opening_stock_total_value = fields.Float('Plan Opening Stock Total Value (Birr)', compute='_compute_plan_opening_stock_total')

    # Computed fields methods
    @api.depends('plan_site_visits', 'plan_office_visits', 'actual_site_visits', 'actual_office_visits',
                 'actual_previous_week_site_visits', 'actual_previous_week_office_visits')
    def _compute_total_visits(self):
        for record in self:
            record.plan_total_visits = record.plan_site_visits + record.plan_office_visits
            record.actual_total_visits = record.actual_site_visits + record.actual_office_visits
            record.actual_previous_week_total_visits = record.actual_previous_week_site_visits + record.actual_previous_week_office_visits
    
    @api.depends('actual_this_week_site_visits', 'actual_this_week_office_visits')
    def _compute_this_week_total_visits(self):
        """Calculate this week total visits (site + office)"""
        for record in self:
            record.actual_this_week_total_visits = (record.actual_this_week_site_visits or 0) + (record.actual_this_week_office_visits or 0)
    
    @api.depends('actual_prospects', 'actual_previous_week_prospects',
                 'actual_follow_ups', 'actual_previous_week_follow_ups',
                 'actual_site_visits', 'actual_previous_week_site_visits',
                 'actual_office_visits', 'actual_previous_week_office_visits',
                 'actual_total_visits', 'actual_previous_week_total_visits',
                 'actual_unit_reservations', 'actual_previous_week_unit_reservations',
                 'actual_deals_closed', 'actual_previous_week_deals_closed',
                 'actual_cash_collected', 'actual_previous_week_cash_collected',
                 'actual_total_deal_value', 'actual_previous_week_total_deal_value')
    def _compute_week_differences(self):
        """Calculate difference: This week (Monday to today) - Previous week (Previous Monday to Sunday)
        This week = Monday of current week to today
        Previous week = Previous Monday to Sunday (complete previous week)
        Difference = This week actual - Previous week actual
        """
        for record in self:
            # This week (Monday to today) - Previous week (Previous Monday to Sunday)
            record.diff_week_prospects = (record.actual_this_week_prospects or 0) - (record.actual_previous_week_prospects or 0)
            record.diff_week_follow_ups = (record.actual_this_week_follow_ups or 0) - (record.actual_previous_week_follow_ups or 0)
            record.diff_week_site_visits = (record.actual_this_week_site_visits or 0) - (record.actual_previous_week_site_visits or 0)
            record.diff_week_office_visits = (record.actual_this_week_office_visits or 0) - (record.actual_previous_week_office_visits or 0)
            record.diff_week_total_visits = (record.actual_this_week_total_visits or 0) - (record.actual_previous_week_total_visits or 0)
            record.diff_week_unit_reservations = (record.actual_this_week_unit_reservations or 0) - (record.actual_previous_week_unit_reservations or 0)
            record.diff_week_deals_closed = (record.actual_this_week_deals_closed or 0) - (record.actual_previous_week_deals_closed or 0)
            record.diff_week_cash_collected = (record.actual_this_week_cash_collected or 0.0) - (record.actual_previous_week_cash_collected or 0.0)
            record.diff_week_total_deal_value = (record.actual_this_week_total_deal_value or 0.0) - (record.actual_previous_week_total_deal_value or 0.0)

    @api.depends('plan_prospects', 'actual_prospects',
                 'plan_follow_ups', 'actual_follow_ups',
                 'plan_site_visits', 'actual_site_visits',
                 'plan_office_visits', 'actual_office_visits',
                 'plan_total_visits', 'actual_total_visits',
                 'plan_unit_reservations', 'actual_unit_reservations',
                 'plan_deals_closed', 'actual_deals_closed',
                 'plan_cash_collected', 'actual_cash_collected',
                 'plan_total_deal_value', 'actual_total_deal_value')
    def _compute_differences(self):
        """Calculate difference: Actual - Plan (positive means actual exceeded plan)"""
        for record in self:
            record.diff_prospects = (record.actual_prospects or 0) - (record.plan_prospects or 0)
            record.diff_follow_ups = (record.actual_follow_ups or 0) - (record.plan_follow_ups or 0)
            record.diff_site_visits = (record.actual_site_visits or 0) - (record.plan_site_visits or 0)
            record.diff_office_visits = (record.actual_office_visits or 0) - (record.plan_office_visits or 0)
            record.diff_total_visits = (record.actual_total_visits or 0) - (record.plan_total_visits or 0)
            record.diff_unit_reservations = (record.actual_unit_reservations or 0) - (record.plan_unit_reservations or 0)
            record.diff_deals_closed = (record.actual_deals_closed or 0) - (record.plan_deals_closed or 0)
            record.diff_cash_collected = (record.actual_cash_collected or 0.0) - (record.plan_cash_collected or 0.0)
            record.diff_total_deal_value = (record.actual_total_deal_value or 0.0) - (record.plan_total_deal_value or 0.0)

    @api.depends('plan_prospects', 'actual_prospects',
                 'plan_follow_ups', 'actual_follow_ups',
                 'plan_site_visits', 'actual_site_visits',
                 'plan_office_visits', 'actual_office_visits',
                 'plan_total_visits', 'actual_total_visits',
                 'plan_unit_reservations', 'actual_unit_reservations',
                 'plan_deals_closed', 'actual_deals_closed',
                 'plan_cash_collected', 'actual_cash_collected',
                 'plan_total_deal_value', 'actual_total_deal_value')
    def _compute_percentages(self):
        for record in self:
            # Calculate percentages (avoid division by zero)
            record.percent_prospects = record._calculate_percentage(record.actual_prospects, record.plan_prospects)
            record.percent_follow_ups = record._calculate_percentage(record.actual_follow_ups, record.plan_follow_ups)
            record.percent_site_visits = record._calculate_percentage(record.actual_site_visits,
                                                                      record.plan_site_visits)
            record.percent_office_visits = record._calculate_percentage(record.actual_office_visits,
                                                                        record.plan_office_visits)
            record.percent_total_visits = record._calculate_percentage(record.actual_total_visits,
                                                                       record.plan_total_visits)
            record.percent_unit_reservations = record._calculate_percentage(record.actual_unit_reservations,
                                                                            record.plan_unit_reservations)
            record.percent_deals_closed = record._calculate_percentage(record.actual_deals_closed,
                                                                       record.plan_deals_closed)
            record.percent_cash_collected = record._calculate_percentage(record.actual_cash_collected,
                                                                         record.plan_cash_collected)
            record.percent_total_deal_value = record._calculate_percentage(record.actual_total_deal_value,
                                                                           record.plan_total_deal_value)

    @api.depends('actual_prospects', 'actual_deals_closed')
    def _compute_conversion_rate(self):
        """Calculate conversion ratio: deals closed / prospects."""
        for record in self:
            try:
                if record.actual_prospects == 0 or record.actual_prospects is None:
                    record.conversion_rate = 0.0
                else:
                    # Conversion = deals closed / prospects (ratio, not percent)
                    record.conversion_rate = round((record.actual_deals_closed / record.actual_prospects), 4)
                _logger.info(f"=== CONVERSION RATE: {record.conversion_rate} (deals_closed={record.actual_deals_closed}, prospects={record.actual_prospects})")
            except Exception as e:
                _logger.error(f"Error computing conversion rate: {str(e)}", exc_info=True)
                record.conversion_rate = 0.0
    
    @api.depends('actual_previous_week_deals_closed', 'actual_previous_week_prospects')
    def _compute_previous_week_conversion_rate(self):
        """Calculate previous week conversion ratio: deals closed / prospects."""
        for record in self:
            try:
                if record.actual_previous_week_prospects == 0 or record.actual_previous_week_prospects is None:
                    record.actual_previous_week_conversion_rate = 0.0
                else:
                    record.actual_previous_week_conversion_rate = round((record.actual_previous_week_deals_closed / record.actual_previous_week_prospects), 4)
            except Exception as e:
                _logger.error(f"Error computing previous week conversion rate: {str(e)}", exc_info=True)
                record.actual_previous_week_conversion_rate = 0.0

    @api.depends('actual_previous_week_total_deal_value', 'opening_stock_total_value', 'plan_opening_stock_total_value')
    def _compute_previous_week_iar_rate(self):
        """Calculate previous week IAR based on opening stock value"""
        for record in self:
            try:
                plan_total_value = record.plan_opening_stock_total_value or 0.0
                actual_total_value = record.opening_stock_total_value or 0.0
                denominator = plan_total_value if plan_total_value > 0 else actual_total_value
                if denominator == 0:
                    record.actual_previous_week_iar_rate = 0.0
                else:
                    record.actual_previous_week_iar_rate = round((record.actual_previous_week_total_deal_value / denominator) * 100, 2)
            except Exception as e:
                _logger.error(f"Error computing previous week IAR rate: {str(e)}", exc_info=True)
                record.actual_previous_week_iar_rate = 0.0

    @api.depends('conversion_rate', 'plan_conversion_rate', 'actual_previous_week_conversion_rate',
                 'iar_rate', 'plan_iar_rate', 'actual_previous_week_iar_rate')
    def _compute_rate_differences(self):
        """Compute differences for conversion and IAR rates"""
        for record in self:
            record.diff_conversion_rate = (record.conversion_rate or 0.0) - (record.plan_conversion_rate or 0.0)
            record.diff_week_conversion_rate = (record.conversion_rate or 0.0) - (record.actual_previous_week_conversion_rate or 0.0)
            record.diff_iar_rate = (record.iar_rate or 0.0) - (record.plan_iar_rate or 0.0)
            record.diff_week_iar_rate = (record.iar_rate or 0.0) - (record.actual_previous_week_iar_rate or 0.0)

    @api.depends('conversion_rate', 'plan_conversion_rate', 'iar_rate', 'plan_iar_rate')
    def _compute_rate_percentages(self):
        """Compute achievement percentages for conversion and IAR"""
        for record in self:
            record.percent_conversion_rate = record._calculate_percentage(record.conversion_rate, record.plan_conversion_rate)
            record.percent_iar_rate = record._calculate_percentage(record.iar_rate, record.plan_iar_rate)
    
    @api.depends('actual_total_deal_value', 'opening_stock_total_value', 'plan_opening_stock_total_value')
    def _compute_iar_rate(self):
        """Calculate IAR: (sales / opening stock estimated value) * 100"""
        for record in self:
            plan_total_value = record.plan_opening_stock_total_value or 0.0
            actual_total_value = record.opening_stock_total_value or 0.0
            denominator = plan_total_value if plan_total_value > 0 else actual_total_value
            if denominator == 0:
                record.iar_rate = 0.0
            else:
                record.iar_rate = round((record.actual_total_deal_value / denominator) * 100, 2)
    
    @api.depends('opening_stock_residence_qty', 'opening_stock_residence_value',
                 'opening_stock_shops_qty', 'opening_stock_shops_value')
    def _compute_opening_stock_total(self):
        """Calculate total opening stock"""
        for record in self:
            record.opening_stock_total_qty = record.opening_stock_residence_qty + record.opening_stock_shops_qty
            record.opening_stock_total_value = record.opening_stock_residence_value + record.opening_stock_shops_value

    @api.depends('plan_opening_stock_residence_qty', 'plan_opening_stock_residence_value',
                 'plan_opening_stock_shops_qty', 'plan_opening_stock_shops_value')
    def _compute_plan_opening_stock_total(self):
        """Calculate total plan opening stock"""
        for record in self:
            record.plan_opening_stock_total_qty = (record.plan_opening_stock_residence_qty or 0) + (record.plan_opening_stock_shops_qty or 0)
            record.plan_opening_stock_total_value = (record.plan_opening_stock_residence_value or 0.0) + (record.plan_opening_stock_shops_value or 0.0)

    def _calculate_percentage(self, actual, plan):
        """Calculate percentage, handle division by zero"""
        if plan == 0 or plan is None or plan == 0.0:
            return 0.0
        if actual is None:
            actual = 0
        percentage = (actual / plan) * 100
        # Cap at 100% for display
        return round(min(percentage, 100.0), 2)

    @api.model
    def default_get(self, fields_list):
        """Set default report_type from context"""
        res = super().default_get(fields_list)
        if 'default_report_type' in self.env.context:
            res['report_type'] = self.env.context.get('default_report_type')
        return res
    
    @api.model
    def check_user_permission(self):
        """Check if current user is supervisor or wing manager"""
        user = self.env.user
        is_supervisor = self.env['property.sales.supervisor'].search_count([('name', '=', user.id)]) > 0
        is_wing_manager = self.env['property.sales.wing'].search_count([('manager_id', '=', user.id)]) > 0
        return is_supervisor or is_wing_manager
    
    @api.model
    def create(self, vals):
        """Override create to auto-generate report after creation"""
        record = super().create(vals)
        # Auto-generate report if we have required fields
        # Wrap in try-except to prevent record deletion if _generate_report fails
        try:
            if record.report_type and ((record.report_type == 'wing' and record.wing_id) or 
                                       (record.report_type == 'supervisor' and record.supervisor_id)) and \
               record.date_from and record.date_to:
                # Check if record still exists before calling _generate_report
                if record.exists():
                    record._generate_report()
        except Exception as e:
            _logger.error(f"Error in _generate_report during create: {str(e)}", exc_info=True)
            # Don't re-raise - allow the record to be created even if generation fails
            # The report can be generated later manually
        return record

    @api.onchange('wing_id', 'supervisor_id', 'date_from', 'date_to')
    def _onchange_parameters(self):
        """Auto-generate report when parameters change"""
        self._generate_report()
    
    def action_refresh_report(self):
        """Public method to refresh the report"""
        self._generate_report()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Report Refreshed'),
                'message': _('The report has been updated with the latest data.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_export_pdf(self):
        """Export report to PDF"""
        self.ensure_one()
        return self.env.ref('sales_plan_report.action_report_sales_performance').report_action(self)
    
    def action_export_excel(self):
        """Export report to Excel using CSV format (simpler, no dependencies)"""
        self.ensure_one()
        import base64
        import io
        import csv
        
        try:
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = ['Metric', 'Actual Previous Week', 'Plan', 'Actual', 
                      'Difference (This week - Previous week)', 'Difference (Plan - Actual)', '% Achievement']
            writer.writerow(headers)
            
            # Write data rows
            data_rows = [
                ['Prospects (Leads)', self.actual_previous_week_prospects, self.plan_prospects, 
                 self.actual_prospects, self.diff_week_prospects, self.diff_prospects, self.percent_prospects],
                ['Follow-ups', self.actual_previous_week_follow_ups, self.plan_follow_ups, 
                 self.actual_follow_ups, self.diff_week_follow_ups, self.diff_follow_ups, self.percent_follow_ups],
                ['Site Visits', self.actual_previous_week_site_visits, self.plan_site_visits, 
                 self.actual_site_visits, self.diff_week_site_visits, self.diff_site_visits, self.percent_site_visits],
                ['Office Visits', self.actual_previous_week_office_visits, self.plan_office_visits, 
                 self.actual_office_visits, self.diff_week_office_visits, self.diff_office_visits, self.percent_office_visits],
                ['Total Visits (Site + Office)', self.actual_previous_week_total_visits, self.plan_total_visits, 
                 self.actual_total_visits, self.diff_week_total_visits, self.diff_total_visits, self.percent_total_visits],
                ['Total unit reservations', self.actual_previous_week_unit_reservations, self.plan_unit_reservations, 
                 self.actual_unit_reservations, self.diff_week_unit_reservations, self.diff_unit_reservations, self.percent_unit_reservations],
                ['Deals Closed (QTY)', self.actual_previous_week_deals_closed, self.plan_deals_closed, 
                 self.actual_deals_closed, self.diff_week_deals_closed, self.diff_deals_closed, self.percent_deals_closed],
                ['Conversion (sales/leads)', self.actual_previous_week_conversion_rate, self.plan_conversion_rate, 
                 self.conversion_rate, self.diff_week_conversion_rate, self.diff_conversion_rate, self.percent_conversion_rate],
                ['Cash Collected (Birr)', self.actual_previous_week_cash_collected, self.plan_cash_collected, 
                 self.actual_cash_collected, self.diff_week_cash_collected, self.diff_cash_collected, self.percent_cash_collected],
                ['Total Deal Value (Birr)', self.actual_previous_week_total_deal_value, self.plan_total_deal_value, 
                 self.actual_total_deal_value, self.diff_week_total_deal_value, self.diff_total_deal_value, self.percent_total_deal_value],
                ['IAR (sales/opening stock)', self.actual_previous_week_iar_rate, self.plan_iar_rate, 
                 self.iar_rate, self.diff_week_iar_rate, self.diff_iar_rate, self.percent_iar_rate],
            ]
            
            for row in data_rows:
                writer.writerow(row)
            
            # Get CSV content and encode
            csv_content = output.getvalue()
            output.close()
            
            # Create attachment
            filename = f"Sales_Performance_Report_{self.date_from}_{self.date_to}.csv"
            file_data = base64.b64encode(csv_content.encode('utf-8-sig')).decode('utf-8')
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': file_data,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'text/csv',
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Error exporting to Excel/CSV: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Export Error'),
                    'message': _('Error exporting to Excel: %s') % str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def _generate_report(self):
        """Generate report based on current parameters"""
        # Check if record still exists (important for TransientModel)
        if not self.exists():
            _logger.warning("Report record does not exist, skipping generation")
            return
        
        # Check if we have all required parameters
        if self.report_type == 'wing' and not self.wing_id:
            self._reset_report_values()
            return
        if self.report_type == 'supervisor' and not self.supervisor_id:
            self._reset_report_values()
            return
        if not self.date_from or not self.date_to:
            self._reset_report_values()
            return

        try:
            # Verify record still exists before each operation
            if not self.exists():
                _logger.warning("Report record deleted before data fetch")
                return
            
            # Get actual data (selected date range)
            self._fetch_actual_data()
            
            # Verify record still exists
            if not self.exists():
                _logger.warning("Report record deleted after _fetch_actual_data")
                return
            
            # Get this week data (Monday to today)
            self._fetch_this_week_data()
            
            # Verify record still exists
            if not self.exists():
                _logger.warning("Report record deleted after _fetch_this_week_data")
                return
            
            # Get previous week data (Previous Monday to Sunday)
            self._fetch_previous_week_data()
            
            # Verify record still exists
            if not self.exists():
                _logger.warning("Report record deleted after _fetch_previous_week_data")
                return
            
            # Get plan data
            self._fetch_plan_data()
            
            # Verify record still exists
            if not self.exists():
                _logger.warning("Report record deleted after _fetch_plan_data")
                return
            
            # Fetch opening stock data
            self._fetch_opening_stock()
            
            # Verify record still exists before accessing computed fields
            if not self.exists():
                _logger.warning("Report record deleted after _fetch_opening_stock")
                return
            
            # Force computation of conversion_rate, previous week conversion_rate, and iar_rate by accessing them
            # This ensures they are computed after all data is fetched
            # Use try-except to handle any errors gracefully
            try:
                _ = self.conversion_rate
            except Exception as e:
                _logger.warning(f"Error computing conversion_rate: {str(e)}")
            
            try:
                _ = self.actual_previous_week_conversion_rate
            except Exception as e:
                _logger.warning(f"Error computing actual_previous_week_conversion_rate: {str(e)}")
            
            try:
                _ = self.iar_rate
            except Exception as e:
                _logger.warning(f"Error computing iar_rate: {str(e)}")

        except Exception as e:
            _logger.error(f"Error generating report: {str(e)}", exc_info=True)
            # Only reset values if record still exists
            if self.exists():
                try:
                    self._reset_report_values()
                except Exception as reset_error:
                    _logger.error(f"Error resetting report values: {str(reset_error)}")
    
    def _fetch_opening_stock(self):
        """Fetch opening stock data for IAR calculation
        Opening stock = properties that are available (state='available') at the start of the period
        """
        try:
            # Count properties that are available (not sold) at the start of the period
            # Opening stock = properties with state='available' before the date_from
            opening_stock_query = """
                SELECT 
                    COUNT(CASE WHEN property_type = 'residence' THEN 1 END) as residence_qty,
                    COALESCE(SUM(CASE WHEN property_type = 'residence' THEN unit_price ELSE 0 END), 0) as residence_value,
                    COUNT(CASE WHEN property_type = 'shop' THEN 1 END) as shops_qty,
                    COALESCE(SUM(CASE WHEN property_type = 'shop' THEN unit_price ELSE 0 END), 0) as shops_value
                FROM property_property
                WHERE state = 'available'
                  AND (create_date < %s OR create_date IS NULL)
            """
            self.env.cr.execute(opening_stock_query, (datetime.combine(self.date_from, datetime.min.time()),))
            result = self.env.cr.fetchone()
            
            if result:
                self.opening_stock_residence_qty = result[0] or 0
                self.opening_stock_residence_value = result[1] or 0.0
                self.opening_stock_shops_qty = result[2] or 0
                self.opening_stock_shops_value = result[3] or 0.0
            else:
                self.opening_stock_residence_qty = 0
                self.opening_stock_residence_value = 0.0
                self.opening_stock_shops_qty = 0
                self.opening_stock_shops_value = 0.0
            
            _logger.info(f"Opening stock data fetched: Residence QTY={self.opening_stock_residence_qty}, Shops QTY={self.opening_stock_shops_qty}, Total QTY={self.opening_stock_total_qty}")
        except Exception as e:
            _logger.error(f"Error fetching opening stock: {str(e)}", exc_info=True)
            try:
                self.env.cr.rollback()  # Rollback transaction on error
            except:
                pass  # Ignore rollback errors
            self.opening_stock_residence_qty = 0
            self.opening_stock_residence_value = 0.0
            self.opening_stock_shops_qty = 0
            self.opening_stock_shops_value = 0.0

    def _reset_report_values(self):
        """Reset all report values to zero"""
        self.plan_prospects = 0
        self.actual_prospects = 0
        self.actual_previous_week_prospects = 0
        self.plan_follow_ups = 0
        self.actual_follow_ups = 0
        self.actual_previous_week_follow_ups = 0
        self.plan_site_visits = 0
        self.actual_site_visits = 0
        self.actual_previous_week_site_visits = 0
        self.plan_office_visits = 0
        self.actual_office_visits = 0
        self.actual_previous_week_office_visits = 0
        self.plan_unit_reservations = 0
        self.actual_unit_reservations = 0
        self.actual_previous_week_unit_reservations = 0
        self.plan_deals_closed = 0
        self.actual_deals_closed = 0
        self.actual_previous_week_deals_closed = 0
        self.plan_conversion_rate = 0.0
        self.plan_iar_rate = 0.0
        self.plan_opening_stock_residence_qty = 0
        self.plan_opening_stock_residence_value = 0.0
        self.plan_opening_stock_shops_qty = 0
        self.plan_opening_stock_shops_value = 0.0
        self.plan_cash_collected = 0.0
        self.actual_cash_collected = 0.0
        self.actual_previous_week_cash_collected = 0.0
        self.plan_total_deal_value = 0.0
        self.actual_total_deal_value = 0.0
        self.actual_previous_week_total_deal_value = 0.0
    
    def _get_this_week_dates(self):
        """Calculate this week date range - Monday of current week to today (or end of selected date range)
        This week = Monday of current week to today (or date_to if selected)
        Example: If today is Wednesday Dec 18, this week = Monday Dec 16 to Wednesday Dec 18
        """
        from datetime import timedelta, date
        today = date.today()
        # Get Monday of current week (weekday() returns 0=Monday, 6=Sunday)
        days_since_monday = today.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
        this_week_from = today - timedelta(days=days_since_monday)  # Monday of this week
        # Use today or date_to (whichever is earlier) as end date
        this_week_to = min(today, self.date_to) if self.date_to else today
        _logger.info(f"=== THIS WEEK CALCULATION: Monday to today/end date")
        _logger.info(f"=== THIS WEEK RANGE: {this_week_from} to {this_week_to}")
        return this_week_from, this_week_to
    
    def _get_previous_week_dates(self):
        """Calculate previous week date range - Previous Monday to Sunday (complete previous week)
        Previous week = Previous Monday to Sunday (complete week before current week)
        Example: If today is Wednesday Dec 18, previous week = Monday Dec 9 to Sunday Dec 15
        """
        from datetime import timedelta, date
        today = date.today()
        # Get Monday of current week
        days_since_monday = today.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
        this_week_monday = today - timedelta(days=days_since_monday)
        # Previous week: Monday to Sunday before current week
        prev_week_sunday = this_week_monday - timedelta(days=1)  # Sunday before this week's Monday
        prev_week_monday = prev_week_sunday - timedelta(days=6)  # Monday of previous week
        _logger.info(f"=== PREVIOUS WEEK CALCULATION: Previous Monday to Sunday")
        _logger.info(f"=== PREVIOUS WEEK RANGE: {prev_week_monday} to {prev_week_sunday}")
        return prev_week_monday, prev_week_sunday
    
    def _fetch_this_week_data(self):
        """Fetch this week actual data - Monday of current week to today
        This week = Monday to today (or end of selected date range if earlier)
        """
        try:
            this_week_from, this_week_to = self._get_this_week_dates()
            _logger.info(f"=== THIS WEEK: Monday to today, Range: {this_week_from} to {this_week_to}")
            
            # Get wing IDs for supervisor reports
            wing_ids = []
            if self.report_type == 'supervisor':
                wing_ids_query = """
                    SELECT id FROM property_sales_wing 
                    WHERE supervisor_id = %s
                """
                self.env.cr.execute(wing_ids_query, (self.supervisor_id.id,))
                wing_ids = [row[0] for row in self.env.cr.fetchall()]
            
            # Get user_ids for this week data
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            
            if report_user_ids:
                start_datetime = datetime.combine(this_week_from, datetime.min.time())
                end_datetime = datetime.combine(this_week_to, datetime.max.time())
                
                # 1. Prospects - Count temer_lead and crm_lead
                if report_user_ids:
                    temer_query = """
                        SELECT COUNT(*) FROM temer_lead tl
                        WHERE tl.user_id IN %s AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(temer_query, (tuple(report_user_ids), this_week_from, this_week_to))
                    temer_prospects = self.env.cr.fetchone()[0] or 0
                    crm_query = """
                        SELECT COUNT(*) FROM crm_lead cl
                        WHERE cl.user_id IN %s AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(crm_query, (tuple(report_user_ids), this_week_from, this_week_to))
                    crm_prospects = self.env.cr.fetchone()[0] or 0
                elif self.report_type == 'wing':
                    temer_query = """
                        SELECT COUNT(*) FROM temer_lead tl
                        WHERE tl.wing_id = %s AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(temer_query, (self.wing_id.id, this_week_from, this_week_to))
                    temer_prospects = self.env.cr.fetchone()[0] or 0
                    crm_query = """
                        SELECT COUNT(*) FROM crm_lead cl
                        WHERE cl.wing_id = %s AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(crm_query, (self.wing_id.id, this_week_from, this_week_to))
                    crm_prospects = self.env.cr.fetchone()[0] or 0
                else:
                    if wing_ids:
                        placeholders = ','.join(['%s'] * len(wing_ids))
                        temer_query = f"""
                            SELECT COUNT(*) FROM temer_lead tl
                            WHERE (tl.supervisor_id = %s OR tl.wing_id IN ({placeholders}))
                            AND DATE(tl.create_date) BETWEEN %s AND %s
                        """
                        params = [self.supervisor_id.id] + wing_ids + [this_week_from, this_week_to]
                        self.env.cr.execute(temer_query, params)
                        temer_prospects = self.env.cr.fetchone()[0] or 0
                        crm_query = f"""
                            SELECT COUNT(*) FROM crm_lead cl
                            WHERE (cl.supervisor_id = %s OR cl.wing_id IN ({placeholders}))
                            AND DATE(cl.create_date) BETWEEN %s AND %s
                        """
                        params = [self.supervisor_id.id] + wing_ids + [this_week_from, this_week_to]
                        self.env.cr.execute(crm_query, params)
                        crm_prospects = self.env.cr.fetchone()[0] or 0
                    else:
                        temer_query = """
                            SELECT COUNT(*) FROM temer_lead tl
                            WHERE tl.supervisor_id = %s AND DATE(tl.create_date) BETWEEN %s AND %s
                        """
                        self.env.cr.execute(temer_query, (self.supervisor_id.id, this_week_from, this_week_to))
                        temer_prospects = self.env.cr.fetchone()[0] or 0
                        crm_query = """
                            SELECT COUNT(*) FROM crm_lead cl
                            WHERE cl.supervisor_id = %s AND DATE(cl.create_date) BETWEEN %s AND %s
                        """
                        self.env.cr.execute(crm_query, (self.supervisor_id.id, this_week_from, this_week_to))
                        crm_prospects = self.env.cr.fetchone()[0] or 0
                self.actual_this_week_prospects = temer_prospects + crm_prospects
                
                # 2. Follow-ups - Count follow-up activities
                follow_ups_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                """
                self.env.cr.execute(follow_ups_query, (this_week_from, this_week_to, tuple(report_user_ids)))
                self.actual_this_week_follow_ups = self.env.cr.fetchone()[0] or 0
                
                # 3. Site and Office Visits (activities)
                site_visits_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'site_visit'
                """
                self.env.cr.execute(site_visits_query, (this_week_from, this_week_to, tuple(report_user_ids)))
                self.actual_this_week_site_visits = self.env.cr.fetchone()[0] or 0
                
                office_visits_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'office_visit'
                """
                self.env.cr.execute(office_visits_query, (this_week_from, this_week_to, tuple(report_user_ids)))
                self.actual_this_week_office_visits = self.env.cr.fetchone()[0] or 0
                
                # 4. Unit Reservations
                placeholders = ','.join(['%s'] * len(report_user_ids))
                reservations_query = f"""
                    SELECT COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                    WHERE pr.salesperson_ids IN ({placeholders})
                      AND DATE(pr.create_date) BETWEEN %s AND %s
                      AND pr.status IN ('reserved', 'requested', 'pending_sales')
                      AND prc.reservation_type IN ('quick', 'regular')
                """
                params = report_user_ids + [this_week_from, this_week_to]
                self.env.cr.execute(reservations_query, params)
                self.actual_this_week_unit_reservations = self.env.cr.fetchone()[0] or 0
                
                # 5. Deals Closed
                deals_query = """
                    SELECT COUNT(*)
                    FROM property_sale ps
                    WHERE DATE(ps.create_date) BETWEEN %s AND %s
                      AND ps.state = 'confirm'
                      AND (ps.sales_person IN %s OR ps.create_uid IN %s)
                """
                self.env.cr.execute(deals_query, (this_week_from, this_week_to, tuple(report_user_ids), tuple(report_user_ids)))
                self.actual_this_week_deals_closed = self.env.cr.fetchone()[0] or 0
                
                # 6. Cash Collected
                placeholders = ','.join(['%s'] * len(report_user_ids))
                cash_query = f"""
                    SELECT COALESCE(SUM(COALESCE(prp.amount, 0)), 0)
                    FROM property_reservation_payment prp
                    JOIN property_reservation pr ON pr.id = prp.reservation_id
                    JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                    WHERE pr.salesperson_ids IN ({placeholders})
                      AND DATE(prp.transaction_date) BETWEEN %s AND %s
                      AND prp.payment_status = 'approved'
                      AND pr.status NOT IN ('canceled', 'expired')
                      AND prc.reservation_type IN ('quick', 'regular')
                """
                params = report_user_ids + [this_week_from, this_week_to]
                self.env.cr.execute(cash_query, params)
                result = self.env.cr.fetchone()
                self.actual_this_week_cash_collected = result[0] if result and result[0] else 0.0
                
                # 7. Total Deal Value
                total_deal_value_query = f"""
                    SELECT COALESCE(SUM(COALESCE(ps.sale_price, 0)), 0)
                    FROM property_sale ps
                    WHERE (ps.sales_person IN ({placeholders}) OR ps.create_uid IN ({placeholders}))
                      AND DATE(ps.create_date) BETWEEN %s AND %s
                      AND ps.state = 'confirm'
                """
                params = report_user_ids + report_user_ids + [this_week_from, this_week_to]
                self.env.cr.execute(total_deal_value_query, params)
                result = self.env.cr.fetchone()
                self.actual_this_week_total_deal_value = result[0] if result and result[0] else 0.0
                
                _logger.info(f"=== THIS WEEK DATA: Prospects={self.actual_this_week_prospects}, Follow-ups={self.actual_this_week_follow_ups}, "
                            f"Site={self.actual_this_week_site_visits}, Office={self.actual_this_week_office_visits}, "
                            f"Reservations={self.actual_this_week_unit_reservations}, Deals={self.actual_this_week_deals_closed}, "
                            f"Cash={self.actual_this_week_cash_collected}, DealValue={self.actual_this_week_total_deal_value}")
            else:
                # No user_ids found
                self.actual_this_week_prospects = 0
                self.actual_this_week_follow_ups = 0
                self.actual_this_week_site_visits = 0
                self.actual_this_week_office_visits = 0
                self.actual_this_week_unit_reservations = 0
                self.actual_this_week_deals_closed = 0
                self.actual_this_week_cash_collected = 0.0
                self.actual_this_week_total_deal_value = 0.0
        except Exception as e:
            _logger.error(f"Error fetching this week data: {str(e)}", exc_info=True)
            try:
                self.env.cr.rollback()  # Rollback transaction on error
            except:
                pass  # Ignore rollback errors
            self.actual_this_week_prospects = 0
            self.actual_this_week_follow_ups = 0
            self.actual_this_week_site_visits = 0
            self.actual_this_week_office_visits = 0
            self.actual_this_week_unit_reservations = 0
            self.actual_this_week_deals_closed = 0
            self.actual_this_week_cash_collected = 0.0
            self.actual_this_week_total_deal_value = 0.0
    
    def _fetch_previous_week_data(self):
        """Fetch previous week actual data - Previous Monday to Sunday (complete previous week)
        Previous week = Previous Monday to Sunday (complete week before current week)
        """
        try:
            prev_week_from, prev_week_to = self._get_previous_week_dates()
            _logger.info(f"=== PREVIOUS WEEK: Previous Monday to Sunday, "
                        f"Previous week range: {prev_week_from} to {prev_week_to}")
            
            # Get wing IDs for supervisor reports
            wing_ids = []
            if self.report_type == 'supervisor':
                wing_ids_query = """
                    SELECT id FROM property_sales_wing 
                    WHERE supervisor_id = %s
                """
                self.env.cr.execute(wing_ids_query, (self.supervisor_id.id,))
                wing_ids = [row[0] for row in self.env.cr.fetchall()]

            # 1. Get Previous Week Prospects
            prev_week_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            if prev_week_user_ids:
                temer_query = """
                    SELECT COUNT(*) FROM temer_lead tl
                    WHERE tl.user_id IN %s AND DATE(tl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(temer_query, (tuple(prev_week_user_ids), prev_week_from, prev_week_to))
                temer_prospects = self.env.cr.fetchone()[0] or 0
                crm_query = """
                    SELECT COUNT(*) FROM crm_lead cl
                    WHERE cl.user_id IN %s AND DATE(cl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(crm_query, (tuple(prev_week_user_ids), prev_week_from, prev_week_to))
                crm_prospects = self.env.cr.fetchone()[0] or 0
            elif self.report_type == 'wing':
                temer_query = """
                    SELECT COUNT(*) FROM temer_lead tl
                    WHERE tl.wing_id = %s AND DATE(tl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(temer_query, (self.wing_id.id, prev_week_from, prev_week_to))
                temer_prospects = self.env.cr.fetchone()[0] or 0
                crm_query = """
                    SELECT COUNT(*) FROM crm_lead cl
                    WHERE cl.wing_id = %s AND DATE(cl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(crm_query, (self.wing_id.id, prev_week_from, prev_week_to))
                crm_prospects = self.env.cr.fetchone()[0] or 0
            else:
                if wing_ids:
                    placeholders = ','.join(['%s'] * len(wing_ids))
                    temer_query = f"""
                        SELECT COUNT(*) FROM temer_lead tl
                        WHERE (tl.supervisor_id = %s OR tl.wing_id IN ({placeholders}))
                        AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    params = [self.supervisor_id.id] + wing_ids + [prev_week_from, prev_week_to]
                    self.env.cr.execute(temer_query, params)
                    temer_prospects = self.env.cr.fetchone()[0] or 0
                    crm_query = f"""
                        SELECT COUNT(*) FROM crm_lead cl
                        WHERE (cl.supervisor_id = %s OR cl.wing_id IN ({placeholders}))
                        AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(crm_query, params)
                    crm_prospects = self.env.cr.fetchone()[0] or 0
                else:
                    temer_query = """
                        SELECT COUNT(*) FROM temer_lead tl
                        WHERE tl.supervisor_id = %s AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(temer_query, (self.supervisor_id.id, prev_week_from, prev_week_to))
                    temer_prospects = self.env.cr.fetchone()[0] or 0
                    crm_query = """
                        SELECT COUNT(*) FROM crm_lead cl
                        WHERE cl.supervisor_id = %s AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(crm_query, (self.supervisor_id.id, prev_week_from, prev_week_to))
                    crm_prospects = self.env.cr.fetchone()[0] or 0
            self.actual_previous_week_prospects = temer_prospects + crm_prospects
            _logger.info(f"=== PREVIOUS WEEK TOTAL PROSPECTS: {self.actual_previous_week_prospects} (temer: {temer_prospects} + crm: {crm_prospects})")

            # 2-4. Previous Week Follow-ups, Site Visits, Office Visits - Use activity table
            user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])

            if user_ids:
                # Follow-ups: Count activities
                query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                """
                self.env.cr.execute(query, (prev_week_from, prev_week_to, tuple(user_ids)))
                self.actual_previous_week_follow_ups = self.env.cr.fetchone()[0] or 0
                
                # Site Visits
                query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'site_visit'
                """
                self.env.cr.execute(query, (prev_week_from, prev_week_to, tuple(user_ids)))
                self.actual_previous_week_site_visits = self.env.cr.fetchone()[0] or 0
                
                # Office Visits
                query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'office_visit'
                """
                self.env.cr.execute(query, (prev_week_from, prev_week_to, tuple(user_ids)))
                self.actual_previous_week_office_visits = self.env.cr.fetchone()[0] or 0
            else:
                self.actual_previous_week_follow_ups = 0
                self.actual_previous_week_site_visits = 0
                self.actual_previous_week_office_visits = 0

            # 5. Previous Week Unit Reservations
            prev_week_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            if prev_week_user_ids:
                placeholders = ','.join(['%s'] * len(prev_week_user_ids))
                query = f"""
                    SELECT COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                    WHERE pr.salesperson_ids IN ({placeholders})
                      AND DATE(pr.create_date) BETWEEN %s AND %s
                      AND pr.status IN ('reserved', 'requested', 'pending_sales')
                      AND prc.reservation_type IN ('quick', 'regular')
                """
                params = prev_week_user_ids + [prev_week_from, prev_week_to]
                self.env.cr.execute(query, params)
                self.actual_previous_week_unit_reservations = self.env.cr.fetchone()[0] or 0
            else:
                self.actual_previous_week_unit_reservations = 0

            # 6. Previous Week Deals Closed - sold qty
            prev_week_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            if prev_week_user_ids:
                query = """
                    SELECT COUNT(*)
                    FROM property_sale ps
                    WHERE DATE(ps.create_date) BETWEEN %s AND %s
                      AND ps.state = 'confirm'
                      AND (ps.sales_person IN %s OR ps.create_uid IN %s)
                """
                self.env.cr.execute(query, (prev_week_from, prev_week_to, tuple(prev_week_user_ids), tuple(prev_week_user_ids)))
                self.actual_previous_week_deals_closed = self.env.cr.fetchone()[0] or 0
            else:
                self.actual_previous_week_deals_closed = 0

            # 7. Previous Week Cash Collected
            # Count collections where sale was created by salesperson OR lead belongs to wing/supervisor
            prev_week_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            try:
                if prev_week_user_ids:
                    placeholders = ','.join(['%s'] * len(prev_week_user_ids))
                    # Count collections where sale was created by user in wing/supervisor
                    cash_query = f"""
                        SELECT COALESCE(SUM(COALESCE(prp.amount, 0)), 0)
                        FROM property_reservation_payment prp
                        JOIN property_reservation pr ON pr.id = prp.reservation_id
                        JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                        WHERE pr.salesperson_ids IN ({placeholders})
                          AND DATE(prp.transaction_date) BETWEEN %s AND %s
                          AND prp.payment_status = 'approved'
                          AND pr.status NOT IN ('canceled', 'expired')
                          AND prc.reservation_type IN ('quick', 'regular')
                    """
                    params = prev_week_user_ids + [prev_week_from, prev_week_to]
                    self.env.cr.execute(cash_query, params)
                    result = self.env.cr.fetchone()
                    self.actual_previous_week_cash_collected = result[0] if result and result[0] else 0.0
                    _logger.info(f"=== PREVIOUS WEEK CASH COLLECTED (filtered by salesperson OR leads): {self.actual_previous_week_cash_collected} for user_ids {prev_week_user_ids} (date range: {prev_week_from} to {prev_week_to})")
                else:
                    self.actual_previous_week_cash_collected = 0.0
            except Exception as e:
                _logger.error(f"Error calculating previous week cash collected: {str(e)}", exc_info=True)
                try:
                    self.env.cr.rollback()  # Rollback transaction on error
                except:
                    pass  # Ignore rollback errors
                self.actual_previous_week_cash_collected = 0.0

            # 8. Previous Week Total Deal Value
            prev_week_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            try:
                if prev_week_user_ids:
                    placeholders = ','.join(['%s'] * len(prev_week_user_ids))
                    prev_week_total_deal_value_query = f"""
                        SELECT COALESCE(SUM(COALESCE(ps.sale_price, 0)), 0)
                        FROM property_sale ps
                        WHERE (ps.sales_person IN ({placeholders}) OR ps.create_uid IN ({placeholders}))
                          AND DATE(ps.create_date) BETWEEN %s AND %s
                          AND ps.state = 'confirm'
                    """
                    params = prev_week_user_ids + prev_week_user_ids + [prev_week_from, prev_week_to]
                    self.env.cr.execute(prev_week_total_deal_value_query, params)
                    result = self.env.cr.fetchone()
                    self.actual_previous_week_total_deal_value = result[0] if result and result[0] else 0.0
                    _logger.info(f"=== PREVIOUS WEEK TOTAL DEAL VALUE: {self.actual_previous_week_total_deal_value} for user_ids {prev_week_user_ids} (date range: {prev_week_from} to {prev_week_to})")
                else:
                    self.actual_previous_week_total_deal_value = 0.0
            except Exception as e:
                _logger.error(f"Error calculating previous week total deal value: {str(e)}", exc_info=True)
                try:
                    self.env.cr.rollback()  # Rollback transaction on error
                except:
                    pass  # Ignore rollback errors
                self.actual_previous_week_total_deal_value = 0.0

        except Exception as e:
            _logger.error(f"Error fetching previous week data: {str(e)}", exc_info=True)
            try:
                self.env.cr.rollback()  # Rollback transaction on error
            except:
                pass  # Ignore rollback errors

    def _fetch_actual_data(self):
        """Fetch actual data from temer_lead and crm_lead tables"""
        try:
            # Get wing IDs for supervisor reports (needed for cash collected calculation)
            wing_ids = []
            if self.report_type == 'supervisor':
                wing_ids_query = """
                    SELECT id FROM property_sales_wing 
                    WHERE supervisor_id = %s
                """
                self.env.cr.execute(wing_ids_query, (self.supervisor_id.id,))
                wing_ids = [row[0] for row in self.env.cr.fetchall()]
            
            # Initialize cash collected to 0 in case of errors
            self.actual_cash_collected = 0.0

            # 1. Get Prospects count (ALL leads from BOTH tables in date range)
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            if report_user_ids:
                temer_prospects_query = """
                    SELECT COUNT(*)
                    FROM temer_lead tl
                    WHERE tl.user_id IN %s
                    AND DATE(tl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(temer_prospects_query, (tuple(report_user_ids), self.date_from, self.date_to))
                temer_prospects = self.env.cr.fetchone()[0] or 0

                crm_prospects_query = """
                    SELECT COUNT(*)
                    FROM crm_lead cl
                    WHERE cl.user_id IN %s
                    AND DATE(cl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(crm_prospects_query, (tuple(report_user_ids), self.date_from, self.date_to))
                crm_prospects = self.env.cr.fetchone()[0] or 0
            elif self.report_type == 'wing':
                temer_prospects_query = """
                    SELECT COUNT(*) 
                    FROM temer_lead tl
                    WHERE tl.wing_id = %s
                    AND DATE(tl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(temer_prospects_query, (self.wing_id.id, self.date_from, self.date_to))
                temer_prospects = self.env.cr.fetchone()[0] or 0

                crm_prospects_query = """
                    SELECT COUNT(*) 
                    FROM crm_lead cl
                    WHERE cl.wing_id = %s
                    AND DATE(cl.create_date) BETWEEN %s AND %s
                """
                self.env.cr.execute(crm_prospects_query, (self.wing_id.id, self.date_from, self.date_to))
                crm_prospects = self.env.cr.fetchone()[0] or 0
            else:
                if wing_ids:
                    placeholders = ','.join(['%s'] * len(wing_ids))
                    temer_prospects_query = f"""
                        SELECT COUNT(*) 
                        FROM temer_lead tl
                        WHERE (tl.supervisor_id = %s OR tl.wing_id IN ({placeholders}))
                        AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    params = [self.supervisor_id.id] + wing_ids + [self.date_from, self.date_to]
                    self.env.cr.execute(temer_prospects_query, params)
                    temer_prospects = self.env.cr.fetchone()[0] or 0

                    crm_prospects_query = f"""
                        SELECT COUNT(*) 
                        FROM crm_lead cl
                        WHERE (cl.supervisor_id = %s OR cl.wing_id IN ({placeholders}))
                        AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    params = [self.supervisor_id.id] + wing_ids + [self.date_from, self.date_to]
                    self.env.cr.execute(crm_prospects_query, params)
                    crm_prospects = self.env.cr.fetchone()[0] or 0
                else:
                    temer_prospects_query = """
                        SELECT COUNT(*) 
                        FROM temer_lead tl
                        WHERE tl.supervisor_id = %s
                        AND DATE(tl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(temer_prospects_query, (self.supervisor_id.id, self.date_from, self.date_to))
                    temer_prospects = self.env.cr.fetchone()[0] or 0

                    crm_prospects_query = """
                        SELECT COUNT(*) 
                        FROM crm_lead cl
                        WHERE cl.supervisor_id = %s
                        AND DATE(cl.create_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(crm_prospects_query, (self.supervisor_id.id, self.date_from, self.date_to))
                    crm_prospects = self.env.cr.fetchone()[0] or 0

            # Total prospects from both tables
            self.actual_prospects = temer_prospects + crm_prospects
            _logger.info(f"=== TOTAL PROSPECTS: {self.actual_prospects} (temer: {temer_prospects} + crm: {crm_prospects})")

            # 2. Get Unit Reservations - quick + regular
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            
            if report_user_ids:
                placeholders = ','.join(['%s'] * len(report_user_ids))
                reservations_query = f"""
                    SELECT COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                    WHERE pr.salesperson_ids IN ({placeholders})
                      AND DATE(pr.create_date) BETWEEN %s AND %s
                      AND pr.status IN ('reserved', 'requested', 'pending_sales')
                      AND prc.reservation_type IN ('quick', 'regular')
                """
                params = report_user_ids + [self.date_from, self.date_to]
                self.env.cr.execute(reservations_query, params)
                self.actual_unit_reservations = self.env.cr.fetchone()[0] or 0
                _logger.info(f"=== UNIT RESERVATIONS COUNT (from property.reservation): {self.actual_unit_reservations} for user_ids {report_user_ids} in date range {self.date_from} to {self.date_to}")
            else:
                self.actual_unit_reservations = 0
                _logger.info(f"=== UNIT RESERVATIONS COUNT: 0 (no user_ids found)")

            # 3. Get Deals Closed - sold qty
            if report_user_ids:
                deals_query = """
                    SELECT COUNT(*)
                    FROM property_sale ps
                    WHERE DATE(ps.create_date) BETWEEN %s AND %s
                      AND ps.state = 'confirm'
                      AND (ps.sales_person IN %s OR ps.create_uid IN %s)
                """
                self.env.cr.execute(deals_query, (self.date_from, self.date_to, tuple(report_user_ids), tuple(report_user_ids)))
                self.actual_deals_closed = self.env.cr.fetchone()[0] or 0
                _logger.info(f"=== DEALS CLOSED COUNT (property_sale state='confirm'): {self.actual_deals_closed} for user_ids {report_user_ids} in date range {self.date_from} to {self.date_to}")
            else:
                self.actual_deals_closed = 0
                _logger.info(f"=== DEALS CLOSED COUNT: 0 (no user_ids found)")
            
            # Conversion rate is already calculated in _compute_conversion_rate based on actual_deals_closed / actual_prospects

            # 4. Get Follow-ups, Site Visits, Office Visits - Use same pattern as sales_plan_module
            # Get user_ids based on wing/supervisor (same logic as prospects)
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])

            if report_user_ids:
                start_datetime = datetime.combine(self.date_from, datetime.min.time())
                end_datetime = datetime.combine(self.date_to, datetime.max.time())

                follow_ups_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                """
                self.env.cr.execute(follow_ups_query, (self.date_from, self.date_to, tuple(report_user_ids)))
                self.actual_follow_ups = self.env.cr.fetchone()[0] or 0
                
                site_visits_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'site_visit'
                """
                self.env.cr.execute(site_visits_query, (self.date_from, self.date_to, tuple(report_user_ids)))
                self.actual_site_visits = self.env.cr.fetchone()[0] or 0
                
                office_visits_query = """
                    SELECT COUNT(*)
                    FROM temer_lead_followup fu
                    WHERE DATE(fu.activity_date) BETWEEN %s AND %s
                      AND fu.user_id IN %s
                      AND fu.activity_type = 'office_visit'
                """
                self.env.cr.execute(office_visits_query, (self.date_from, self.date_to, tuple(report_user_ids)))
                self.actual_office_visits = self.env.cr.fetchone()[0] or 0
            else:
                # Fallback by wing/supervisor if no user_ids resolved
                if self.report_type == 'wing':
                    follow_ups_query = """
                        SELECT COUNT(*)
                        FROM temer_lead_followup fu
                        JOIN temer_lead tl ON tl.id = fu.lead_id
                        WHERE tl.wing_id = %s
                          AND DATE(fu.activity_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(follow_ups_query, (self.wing_id.id, self.date_from, self.date_to))
                    self.actual_follow_ups = self.env.cr.fetchone()[0] or 0
                else:
                    follow_ups_query = """
                        SELECT COUNT(*)
                        FROM temer_lead_followup fu
                        JOIN temer_lead tl ON tl.id = fu.lead_id
                        WHERE tl.supervisor_id = %s
                          AND DATE(fu.activity_date) BETWEEN %s AND %s
                    """
                    self.env.cr.execute(follow_ups_query, (self.supervisor_id.id, self.date_from, self.date_to))
                    self.actual_follow_ups = self.env.cr.fetchone()[0] or 0
                self.actual_site_visits = 0
                self.actual_office_visits = 0

            # 7. Cash Collected from reservation advance payments
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            try:
                if report_user_ids:
                    placeholders = ','.join(['%s'] * len(report_user_ids))
                    cash_query = f"""
                        SELECT COALESCE(SUM(COALESCE(prp.amount, 0)), 0)
                        FROM property_reservation_payment prp
                        JOIN property_reservation pr ON pr.id = prp.reservation_id
                        JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                        WHERE pr.salesperson_ids IN ({placeholders})
                          AND DATE(prp.transaction_date) BETWEEN %s AND %s
                          AND prp.payment_status = 'approved'
                          AND pr.status NOT IN ('canceled', 'expired')
                          AND prc.reservation_type IN ('quick', 'regular')
                    """
                    params = report_user_ids + [self.date_from, self.date_to]
                    self.env.cr.execute(cash_query, params)
                    result = self.env.cr.fetchone()
                    self.actual_cash_collected = result[0] if result and result[0] else 0.0
                    _logger.info(f"=== CASH COLLECTED (reservation advance): {self.actual_cash_collected} for user_ids {report_user_ids} (date range: {self.date_from} to {self.date_to})")
                else:
                    self.actual_cash_collected = 0.0
                    _logger.warning(f"=== CASH COLLECTED: 0 (no user_ids found for {self.report_type})")
            except Exception as e:
                _logger.error(f"Error calculating cash collected: {str(e)}", exc_info=True)
                try:
                    self.env.cr.rollback()  # Rollback transaction on error
                except:
                    pass  # Ignore rollback errors
                self.actual_cash_collected = 0.0

            # 8. Get Total Deal Value - Sum of sale_price from property_sale created by selected salespersons
            report_user_ids = self._get_user_ids_for_report(wing_ids if self.report_type == 'supervisor' else [])
            try:
                if report_user_ids:
                    placeholders = ','.join(['%s'] * len(report_user_ids))
                    total_deal_value_query = f"""
                        SELECT COALESCE(SUM(COALESCE(ps.sale_price, 0)), 0)
                        FROM property_sale ps
                        WHERE (ps.sales_person IN ({placeholders}) OR ps.create_uid IN ({placeholders}))
                          AND DATE(ps.create_date) BETWEEN %s AND %s
                          AND ps.state = 'confirm'
                    """
                    params = report_user_ids + report_user_ids + [self.date_from, self.date_to]
                    self.env.cr.execute(total_deal_value_query, params)
                    result = self.env.cr.fetchone()
                    self.actual_total_deal_value = result[0] if result and result[0] else 0.0
                    _logger.info(f"=== TOTAL DEAL VALUE: {self.actual_total_deal_value} for user_ids {report_user_ids} (date range: {self.date_from} to {self.date_to})")
                else:
                    self.actual_total_deal_value = 0.0
            except Exception as e:
                _logger.error(f"Error calculating total deal value: {str(e)}", exc_info=True)
                try:
                    self.env.cr.rollback()  # Rollback transaction on error
                except:
                    pass  # Ignore rollback errors
                self.actual_total_deal_value = 0.0

            _logger.info(f"=== FINAL ACTUAL DATA SUMMARY: Prospects: {self.actual_prospects}, Follow-ups: {self.actual_follow_ups}, "
                        f"Site Visits: {self.actual_site_visits}, Office Visits: {self.actual_office_visits}, "
                        f"Reservations: {self.actual_unit_reservations}, Deals: {self.actual_deals_closed}, "
                        f"Cash Collected: {self.actual_cash_collected}, Total Deal Value: {self.actual_total_deal_value}")
            
            # Force computation of conversion_rate and iar_rate after all data is fetched
            self._compute_conversion_rate()
            self._compute_iar_rate()
            _logger.info(f"=== CONVERSION RATE COMPUTED: {self.conversion_rate} (deals_closed={self.actual_deals_closed}, prospects={self.actual_prospects})")
            _logger.info(f"=== IAR RATE COMPUTED: {self.iar_rate}% (deals_closed={self.actual_deals_closed}, opening_stock={self.opening_stock_total_qty})")

        except Exception as e:
            _logger.error(f"Error fetching actual data: {str(e)}", exc_info=True)
            try:
                self.env.cr.rollback()  # Rollback transaction on error
            except:
                pass  # Ignore rollback errors
            # Set defaults to 0 instead of raising, so report can still be generated
            if not hasattr(self, 'actual_prospects') or self.actual_prospects is None:
                self.actual_prospects = 0
            if not hasattr(self, 'actual_follow_ups') or self.actual_follow_ups is None:
                self.actual_follow_ups = 0
            if not hasattr(self, 'actual_site_visits') or self.actual_site_visits is None:
                self.actual_site_visits = 0
            if not hasattr(self, 'actual_office_visits') or self.actual_office_visits is None:
                self.actual_office_visits = 0
            if not hasattr(self, 'actual_unit_reservations') or self.actual_unit_reservations is None:
                self.actual_unit_reservations = 0
            if not hasattr(self, 'actual_deals_closed') or self.actual_deals_closed is None:
                self.actual_deals_closed = 0
            if not hasattr(self, 'actual_cash_collected') or self.actual_cash_collected is None:
                self.actual_cash_collected = 0.0
    
    def _get_user_ids_for_report(self, wing_ids):
        """Get all user IDs for the report (supervisor + all supervised salespersons + users from wings)"""
        user_ids = set()
        if self.report_type == 'wing':
            if self.wing_id:
                # Get all supervisors and filter by wing in Python (since sales_team_id is non-stored)
                all_supervisors = self.env['property.sales.supervisor'].search([])
                supervisors = all_supervisors.filtered(lambda s: s.sales_team_id and s.sales_team_id.wing_id and s.sales_team_id.wing_id.id == self.wing_id.id)
                user_ids.update(supervisors.mapped('name.id'))
                salesperson_mappings = self.env['property.salesperson.mapping'].search([
                    ('supervisor_id.name', 'in', list(user_ids))
                ])
                user_ids.update(salesperson_mappings.mapped('user_id.id'))
        else:  # supervisor report
            if self.supervisor_id:
                # Get the actual user ID from property.sales.supervisor
                supervisor_user_id = self.supervisor_id.name.id if self.supervisor_id.name else None
                if supervisor_user_id:
                    user_ids.add(supervisor_user_id)
                    # Get salespersons under this supervisor
                    salesperson_mappings = self.env['property.salesperson.mapping'].search([
                        ('supervisor_id.name', '=', supervisor_user_id)
                    ])
                    user_ids.update(salesperson_mappings.mapped('user_id.id'))
                    # Include users from wings under this supervisor
                    if wing_ids:
                        for wing_id in wing_ids:
                            # Get all supervisors and filter by wing in Python (since sales_team_id is non-stored)
                            all_supervisors = self.env['property.sales.supervisor'].search([])
                            wing_supervisors = all_supervisors.filtered(lambda s: s.sales_team_id and s.sales_team_id.wing_id and s.sales_team_id.wing_id.id == wing_id)
                            user_ids.update(wing_supervisors.mapped('name.id'))
                            wing_salesperson_mappings = self.env['property.salesperson.mapping'].search([
                                ('supervisor_id.name', 'in', list(wing_supervisors.mapped('name.id')))
                            ])
                            user_ids.update(wing_salesperson_mappings.mapped('user_id.id'))
        return list(user_ids)

    def _fetch_plan_data(self):
        """Fetch plan data from sales_plan table - includes all plans that overlap with the date range"""
        try:
            # Convert dates to strings
            date_from_str = self.date_from.strftime('%Y-%m-%d')
            date_to_str = self.date_to.strftime('%Y-%m-%d')

            if self.report_type == 'wing':
                # Get all plans that overlap with the selected date range
                # A plan overlaps if: start_date <= report_date_to AND end_date >= report_date_from
                # This means: plan starts before/on report end AND plan ends after/on report start
                # Example: Plan Dec 1, 2025 to Jan 27, 2026, Report Jan 10, 2025 to Dec 30, 2025
                # Dec 1, 2025 <= Dec 30, 2025 (TRUE) AND Jan 27, 2026 >= Jan 10, 2025 (TRUE) = INCLUDED
                plan_query = """
                             SELECT COALESCE(SUM(prospect_plan), 0)         as prospects,
                                    COALESCE(SUM(followup_plan), 0)         as follow_ups,
                                    COALESCE(SUM(site_visit_plan), 0)       as site_visits,
                                    COALESCE(SUM(office_visit_plan), 0)     as office_visits,
                                    COALESCE(SUM(unit_reservation_plan), 0) as unit_reservations,
                                    COALESCE(SUM(deals_closed_plan), 0)     as deals_closed,
                                    COALESCE(SUM(cash_collected_plan), 0)   as cash_collected,
                                    COALESCE(SUM(total_deal_value_plan), 0) as total_deal_value,
                                    COALESCE(AVG(conversion_plan), 0)       as conversion_plan,
                                    COALESCE(AVG(iar_plan), 0)              as iar_plan,
                                    COALESCE(SUM(opening_stock_residence_qty_plan), 0)  as opening_stock_residence_qty_plan,
                                    COALESCE(SUM(opening_stock_residence_value_plan), 0) as opening_stock_residence_value_plan,
                                    COALESCE(SUM(opening_stock_shops_qty_plan), 0)      as opening_stock_shops_qty_plan,
                                    COALESCE(SUM(opening_stock_shops_value_plan), 0)    as opening_stock_shops_value_plan
                             FROM sales_plan
                             WHERE wing_id = %s
                               AND start_date <= %s
                               AND end_date >= %s
                               AND state IN ('draft', 'completed')
                             """
                params = (self.wing_id.id, date_to_str, date_from_str)
                _logger.info(f"=== PLAN OVERLAP LOGIC: Looking for plans where start_date <= {date_to_str} AND end_date >= {date_from_str}")
                _logger.info(f"Fetching plan data for wing {self.wing_id.id} ({self.wing_id.name}) from {date_from_str} to {date_to_str}")
                _logger.info(f"SQL Query: {plan_query}")
                _logger.info(f"SQL Params: {params}")
                
                # Debug: Check what plans exist for this wing
                debug_query = """
                    SELECT id, name, supervisor_id, wing_id, start_date, end_date, state, 
                           prospect_plan, followup_plan, site_visit_plan, office_visit_plan,
                           unit_reservation_plan, deals_closed_plan, cash_collected_plan, total_deal_value_plan
                    FROM sales_plan
                    WHERE wing_id = %s
                    ORDER BY start_date DESC
                    LIMIT 10
                """
                self.env.cr.execute(debug_query, (self.wing_id.id,))
                debug_plans = self.env.cr.fetchall()
                _logger.info(f"=== DEBUG: Found {len(debug_plans)} total plans for wing {self.wing_id.id} ({self.wing_id.name}):")
                for plan in debug_plans:
                    _logger.info(f"  Plan ID {plan[0]}: {plan[1]}, dates: {plan[4]} to {plan[5]}, state: {plan[6]}, "
                               f"prospect={plan[7]}, followup={plan[8]}, site={plan[9]}, office={plan[10]}")
                
                # Also check plans that match date range (without state filter first)
                date_debug_query = """
                    SELECT id, name, supervisor_id, wing_id, start_date, end_date, state, 
                           prospect_plan, followup_plan, site_visit_plan, office_visit_plan,
                           unit_reservation_plan, deals_closed_plan, cash_collected_plan, total_deal_value_plan
                    FROM sales_plan
                    WHERE wing_id = %s
                      AND start_date <= %s
                      AND end_date >= %s
                    ORDER BY start_date DESC
                """
                self.env.cr.execute(date_debug_query, (self.wing_id.id, date_to_str, date_from_str))
                date_debug_plans = self.env.cr.fetchall()
                _logger.info(f"=== DEBUG: Found {len(date_debug_plans)} plans matching date range {date_from_str} to {date_to_str} (before state filter):")
                for plan in date_debug_plans:
                    _logger.info(f"  Plan ID {plan[0]}: {plan[1]}, dates: {plan[4]} to {plan[5]}, state: {plan[6]}, "
                               f"prospect={plan[7]}, followup={plan[8]}, site={plan[9]}, office={plan[10]}")
                
                # Check plans with state filter
                state_debug_query = """
                    SELECT id, name, supervisor_id, wing_id, start_date, end_date, state, 
                           prospect_plan, followup_plan, site_visit_plan, office_visit_plan,
                           unit_reservation_plan, deals_closed_plan, cash_collected_plan, total_deal_value_plan
                    FROM sales_plan
                    WHERE wing_id = %s
                      AND start_date <= %s
                      AND end_date >= %s
                      AND state IN ('draft', 'completed')
                    ORDER BY start_date DESC
                """
                self.env.cr.execute(state_debug_query, (self.wing_id.id, date_to_str, date_from_str))
                state_debug_plans = self.env.cr.fetchall()
                _logger.info(f"=== DEBUG: Found {len(state_debug_plans)} plans matching date range AND state filter:")
                for plan in state_debug_plans:
                    _logger.info(f"  Plan ID {plan[0]}: {plan[1]}, dates: {plan[4]} to {plan[5]}, state: {plan[6]}, "
                               f"prospect={plan[7]}, followup={plan[8]}, site={plan[9]}, office={plan[10]}, "
                               f"reservations={plan[11]}, deals={plan[12]}, cash={plan[13]}, deal_value={plan[14]}")
            else:
                # For supervisor, get the actual user ID from property.sales.supervisor
                # supervisor_id in sales_plan is res.users, not property.sales.supervisor
                supervisor_user_id = self.supervisor_id.name.id if self.supervisor_id.name else None
                
                if not supervisor_user_id:
                    _logger.warning(f"No user ID found for supervisor {self.supervisor_id.id}")
                    self.plan_prospects = 0
                    self.plan_follow_ups = 0
                    self.plan_site_visits = 0
                    self.plan_office_visits = 0
                    self.plan_unit_reservations = 0
                    self.plan_deals_closed = 0
                    self.plan_cash_collected = 0.0
                    self.plan_total_deal_value = 0.0
                    return
                
                # Get all wing IDs for this supervisor
                wing_ids_query = """
                    SELECT id FROM property_sales_wing 
                    WHERE supervisor_id = %s
                """
                self.env.cr.execute(wing_ids_query, (self.supervisor_id.id,))
                wing_ids = [row[0] for row in self.env.cr.fetchall()]
                
                _logger.info(f"Supervisor {self.supervisor_id.id} (user {supervisor_user_id}) has wings: {wing_ids}")
                
                # Get plans directly assigned to supervisor (using user ID) AND plans from wings
                # IMPORTANT: A plan overlaps with date range if:
                # plan.start_date <= report.date_to AND plan.end_date >= report.date_from
                # Example: Plan Dec 1, 2025 to Jan 27, 2026, Report Jan 10, 2025 to Dec 30, 2025
                # Dec 1, 2025 <= Dec 30, 2025 (TRUE) AND Jan 27, 2026 >= Jan 10, 2025 (TRUE) = INCLUDED
                if wing_ids:
                    placeholders = ','.join(['%s'] * len(wing_ids))
                    plan_query = f"""
                                 SELECT COALESCE(SUM(prospect_plan), 0)         as prospects,
                                        COALESCE(SUM(followup_plan), 0)         as follow_ups,
                                        COALESCE(SUM(site_visit_plan), 0)       as site_visits,
                                        COALESCE(SUM(office_visit_plan), 0)     as office_visits,
                                        COALESCE(SUM(unit_reservation_plan), 0) as unit_reservations,
                                        COALESCE(SUM(deals_closed_plan), 0)     as deals_closed,
                                        COALESCE(SUM(cash_collected_plan), 0)   as cash_collected,
                                        COALESCE(SUM(total_deal_value_plan), 0) as total_deal_value,
                                        COALESCE(AVG(conversion_plan), 0)       as conversion_plan,
                                        COALESCE(AVG(iar_plan), 0)              as iar_plan,
                                        COALESCE(SUM(opening_stock_residence_qty_plan), 0)  as opening_stock_residence_qty_plan,
                                        COALESCE(SUM(opening_stock_residence_value_plan), 0) as opening_stock_residence_value_plan,
                                        COALESCE(SUM(opening_stock_shops_qty_plan), 0)      as opening_stock_shops_qty_plan,
                                        COALESCE(SUM(opening_stock_shops_value_plan), 0)    as opening_stock_shops_value_plan
                                 FROM sales_plan
                                 WHERE (supervisor_id = %s OR wing_id IN ({placeholders}))
                                   AND start_date <= %s
                                   AND end_date >= %s
                                   AND state IN ('draft', 'completed')
                                 """
                    params = [supervisor_user_id] + wing_ids + [date_to_str, date_from_str]
                    _logger.info(f"=== PLAN OVERLAP LOGIC (Supervisor): Looking for plans where start_date <= {date_to_str} AND end_date >= {date_from_str}")
                else:
                    # No wings, only supervisor plans
                    plan_query = """
                                 SELECT COALESCE(SUM(prospect_plan), 0)         as prospects,
                                        COALESCE(SUM(followup_plan), 0)         as follow_ups,
                                        COALESCE(SUM(site_visit_plan), 0)       as site_visits,
                                        COALESCE(SUM(office_visit_plan), 0)     as office_visits,
                                        COALESCE(SUM(unit_reservation_plan), 0) as unit_reservations,
                                        COALESCE(SUM(deals_closed_plan), 0)     as deals_closed,
                                        COALESCE(SUM(cash_collected_plan), 0)   as cash_collected,
                                        COALESCE(SUM(total_deal_value_plan), 0) as total_deal_value,
                                        COALESCE(AVG(conversion_plan), 0)       as conversion_plan,
                                        COALESCE(AVG(iar_plan), 0)              as iar_plan,
                                        COALESCE(SUM(opening_stock_residence_qty_plan), 0)  as opening_stock_residence_qty_plan,
                                        COALESCE(SUM(opening_stock_residence_value_plan), 0) as opening_stock_residence_value_plan,
                                        COALESCE(SUM(opening_stock_shops_qty_plan), 0)      as opening_stock_shops_qty_plan,
                                        COALESCE(SUM(opening_stock_shops_value_plan), 0)    as opening_stock_shops_value_plan
                                 FROM sales_plan
                                 WHERE supervisor_id = %s
                                   AND start_date <= %s
                                   AND end_date >= %s
                                   AND state IN ('draft', 'completed')
                                 """
                    params = (supervisor_user_id, date_to_str, date_from_str)
                    _logger.info(f"=== PLAN OVERLAP LOGIC (Supervisor, no wings): Looking for plans where start_date <= {date_to_str} AND end_date >= {date_from_str}")
                _logger.info(f"Fetching plan data for supervisor user {supervisor_user_id} (supervisor record {self.supervisor_id.id}) from {date_from_str} to {date_to_str}")
                _logger.info(f"SQL Query: {plan_query}")
                _logger.info(f"SQL Params: {params}")

            self.env.cr.execute(plan_query, params)
            result = self.env.cr.fetchone()
            _logger.info(f"=== SQL Query Result (SUM): {result}")
            if result:
                _logger.info(f"  Summed values: prospects={result[0]}, followups={result[1]}, site={result[2]}, "
                           f"office={result[3]}, reservations={result[4]}, deals={result[5]}, "
                           f"cash={result[6] if len(result) > 6 else 'N/A'}, deal_value={result[7] if len(result) > 7 else 'N/A'}")
            
            # Also check what plans exist for debugging
            if self.report_type == 'supervisor':
                debug_query = """
                    SELECT id, name, supervisor_id, wing_id, start_date, end_date, state, 
                           prospect_plan, followup_plan, site_visit_plan, office_visit_plan
                    FROM sales_plan
                    WHERE supervisor_id = %s OR wing_id IN %s
                    ORDER BY start_date DESC
                    LIMIT 10
                """
                if wing_ids:
                    self.env.cr.execute(debug_query, (supervisor_user_id, tuple(wing_ids)))
                else:
                    self.env.cr.execute("SELECT id, name, supervisor_id, wing_id, start_date, end_date, state, prospect_plan, followup_plan, site_visit_plan, office_visit_plan FROM sales_plan WHERE supervisor_id = %s ORDER BY start_date DESC LIMIT 10", (supervisor_user_id,))
                debug_plans = self.env.cr.fetchall()
                _logger.info(f"Found {len(debug_plans)} plans for supervisor {supervisor_user_id}: {debug_plans}")

            if result:
                _logger.info(f"SQL Result: {result}")
                self.plan_prospects = result[0] if result[0] is not None else 0
                self.plan_follow_ups = result[1] if result[1] is not None else 0
                self.plan_site_visits = result[2] if result[2] is not None else 0
                self.plan_office_visits = result[3] if result[3] is not None else 0
                self.plan_unit_reservations = result[4] if result[4] is not None else 0
                self.plan_deals_closed = result[5] if result[5] is not None else 0
                if len(result) > 6:
                    self.plan_cash_collected = result[6] if result[6] is not None else 0.0
                    self.plan_total_deal_value = result[7] if result[7] is not None else 0.0
                if len(result) > 8:
                    self.plan_conversion_rate = result[8] if result[8] is not None else 0.0
                    self.plan_iar_rate = result[9] if result[9] is not None else 0.0
                if len(result) > 10:
                    self.plan_opening_stock_residence_qty = result[10] if result[10] is not None else 0
                    self.plan_opening_stock_residence_value = result[11] if result[11] is not None else 0.0
                    self.plan_opening_stock_shops_qty = result[12] if result[12] is not None else 0
                    self.plan_opening_stock_shops_value = result[13] if result[13] is not None else 0.0
                _logger.info(f"Plan data loaded: Prospects={self.plan_prospects}, Follow-ups={self.plan_follow_ups}, "
                           f"Site Visits={self.plan_site_visits}, Office Visits={self.plan_office_visits}, "
                           f"Reservations={self.plan_unit_reservations}, Deals={self.plan_deals_closed}, "
                           f"Cash={self.plan_cash_collected}, Deal Value={self.plan_total_deal_value}")
            else:
                self.plan_prospects = 0
                self.plan_follow_ups = 0
                self.plan_site_visits = 0
                self.plan_office_visits = 0
                self.plan_unit_reservations = 0
                self.plan_deals_closed = 0
                self.plan_conversion_rate = 0.0
                self.plan_iar_rate = 0.0
                self.plan_opening_stock_residence_qty = 0
                self.plan_opening_stock_residence_value = 0.0
                self.plan_opening_stock_shops_qty = 0
                self.plan_opening_stock_shops_value = 0.0
                _logger.warning(f"No plan data found for date range {date_from_str} to {date_to_str}")
                _logger.warning(f"Query was: {plan_query}")
                _logger.warning(f"Params were: {params}")
                _logger.warning(f"Result was: {result}")

        except Exception as e:
            _logger.error(f"Error fetching plan data: {str(e)}", exc_info=True)
            try:
                self.env.cr.rollback()  # Rollback transaction on error
            except:
                pass  # Ignore rollback errors
            self._reset_report_values()