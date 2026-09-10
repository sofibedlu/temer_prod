# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CollectionPlanStage(models.Model):
    _name = 'collection.plan.stage'
    _description = 'Collection Plan Stage'
    _order = 'site_id, id'

    name = fields.Char(string='Plan Name', required=True, default='New Plan')
    site_id = fields.Many2one('property.site', string='Site/Project', required=False, ondelete='set null')
    site_name = fields.Char(string='Site Name', related='site_id.name', store=True, readonly=True)
    planner_id = fields.Many2one('res.users', string='Planner', default=lambda self: self.env.user, required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Date fields for filtering
    date_from = fields.Date(string='Date From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.today)
    
    # Exchange rate (kept for other reports; not shown in Collection Plan form)
    exchange_rate = fields.Float(string='Exchange Rate (ETB to USD)', default=0.0064, digits=(10, 6))
    
    # PLAN section (normal plan, stored in plan model)
    plan_customers = fields.Integer(string='Plan - No of Customers', default=0)
    plan_customers_remark = fields.Char(string='Remark - No of Clients')
    plan_amount_birr = fields.Float(string='Plan - Amount in Birr', default=0.0, digits=(16, 2))
    plan_amount_remark = fields.Char(string='Remark - Collected Amount')
    plan_amount_dollar = fields.Float(string='Plan - Amount in Dollar', compute='_compute_plan_dollar', store=True, digits=(16, 2))
    
    # PENALTY section
    penalty_customers = fields.Integer(string='Penalty - No of Customers', default=0)
    penalty_amount_birr = fields.Float(string='Penalty - Amount in Birr', default=0.0, digits=(16, 2))
    penalty_amount_dollar = fields.Float(string='Penalty - Amount in Dollar', compute='_compute_penalty_dollar', store=True, digits=(16, 2))
    
    # TERMINATION section
    termination_customers = fields.Integer(string='Termination - No of Customers', default=0)
    termination_amount_birr = fields.Float(string='Termination - Amount in Birr', default=0.0, digits=(16, 2))
    termination_amount_dollar = fields.Float(string='Termination - Amount in Dollar', compute='_compute_termination_dollar', store=True, digits=(16, 2))
    
    # TOTAL COLLECTION PLAN section (computed)
    total_customers = fields.Integer(string='Total - No of Customers', compute='_compute_totals', store=True)
    total_amount_birr = fields.Float(string='Total - Amount in Birr', compute='_compute_totals', store=True, digits=(16, 2))
    total_amount_dollar = fields.Float(string='Total - Amount in Dollar', compute='_compute_totals', store=True, digits=(16, 2))
    
    @api.depends('plan_amount_birr', 'exchange_rate')
    def _compute_plan_dollar(self):
        for record in self:
            record.plan_amount_dollar = record.plan_amount_birr * (record.exchange_rate or 0.0064)
    
    @api.depends('penalty_amount_birr', 'exchange_rate')
    def _compute_penalty_dollar(self):
        for record in self:
            record.penalty_amount_dollar = record.penalty_amount_birr * (record.exchange_rate or 0.0064)
    
    @api.depends('termination_amount_birr', 'exchange_rate')
    def _compute_termination_dollar(self):
        for record in self:
            record.termination_amount_dollar = record.termination_amount_birr * (record.exchange_rate or 0.0064)
    
    @api.depends('plan_customers', 'plan_amount_birr', 'plan_amount_dollar')
    def _compute_totals(self):
        for record in self:
            # Total = PLAN only (penalty and termination are not planned)
            record.total_customers = record.plan_customers
            record.total_amount_birr = record.plan_amount_birr
            record.total_amount_dollar = record.plan_amount_dollar
    
    def _generate_plan_name(self):
        """Generate plan name from selected dates and planner name"""
        if self.date_from and self.date_to and self.planner_id:
            date_from_str = self.date_from.strftime('%d %b %Y')
            date_to_str = self.date_to.strftime('%d %b %Y')
            planner_name = self.planner_id.name or 'Unknown'
            return f"{date_from_str} to {date_to_str} - {planner_name}"
        return 'New Plan'
    
    @api.onchange('date_from', 'date_to', 'planner_id')
    def _onchange_generate_plan_name(self):
        """Auto-generate plan name when dates or planner change"""
        if self.date_from and self.date_to and self.planner_id:
            self.name = self._generate_plan_name()
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate plan name"""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New Plan':
                temp_record = self.new(vals)
                generated_name = temp_record._generate_plan_name()
                if generated_name and generated_name != 'New Plan':
                    vals['name'] = generated_name
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('collection.plan.stage') or 'New Plan'
        return super(CollectionPlanStage, self).create(vals_list)
    
    def write(self, vals):
        """Override write to auto-update plan name when dates or planner change"""
        result = super().write(vals)
        if any(key in vals for key in ['date_from', 'date_to', 'planner_id']):
            for record in self:
                record.name = record._generate_plan_name()
        return result
    
    @api.constrains('site_id', 'active')
    def _check_unique_site(self):
        for record in self:
            if record.active and record.site_id:
                existing = self.search([
                    ('site_id', '=', record.site_id.id),
                    ('active', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('An active plan already exists for site %s. Please deactivate the existing plan first.') % record.site_id.name)

