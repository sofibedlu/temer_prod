from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class BenefitDefinition(models.Model):
    _name = 'benefit.definition'
    _description = 'Employee Benefit Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id, benefit_type_id'
    _rec_name = 'display_name'

    department_id = fields.Many2one(
        'hr.department', 
        string='Department', 
        required=True, 
        tracking=True
    )
    employee_id = fields.Many2one(
        'hr.employee', 
        string='Employee', 
        required=True, 
        tracking=True,
        domain="[('department_id', '=', department_id)]"
    )
    benefit_type_id = fields.Many2one(
        'benefit.type', 
        string='Benefit Type', 
        required=True, 
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        default=lambda self: self.env.company.currency_id, 
        required=True
    )
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    benefit_details = fields.Text(string='Benefit Details')
    
    # Recurring Frequency
    interval_number = fields.Integer(string='Every', default=1, required=True, tracking=True)
    interval_unit = fields.Selection([
        ('month', 'Month(s)'),
        ('year', 'Year(s)'),
    ], string='Interval Unit', default='month', required=True, tracking=True)
    
    last_recurring_date = fields.Date(string='Last Recurring Date', tracking=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_emp_benefit', 'unique(employee_id, benefit_type_id)', 
         'This employee already has a definition for this benefit type!')
    ]

    @api.depends('employee_id', 'benefit_type_id')
    def _compute_display_name(self):
        for rec in self:
            emp_name = rec.employee_id.name or _('Unknown')
            benefit_name = rec.benefit_type_id.name or _('Benefit')
            rec.display_name = f"{emp_name} - {benefit_name}"

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.employee_id and self.employee_id.department_id != self.department_id:
            self.employee_id = False

    @api.constrains('interval_number')
    def _check_interval_number(self):
        for rec in self:
            if rec.interval_number <= 0:
                raise ValidationError(_("Recurring frequency ('Every') must be greater than 0."))


    reminder_lead_days = fields.Integer(
        string='Reminder Days Before Expiry', 
        default=5, 
        help="Number of days before expiration to show in the reminder window."
    )

    next_due_date = fields.Date(
        string='Next Expiry / Due Date', 
        compute='_compute_recurring_dates', 
        store=True,
        tracking=True
    )
    reminder_date = fields.Date(
        string='Reminder Trigger Date', 
        compute='_compute_recurring_dates', 
        store=True
    )
    is_reminder_due = fields.Boolean(
        string='Needs Renewal', 
        compute='_compute_is_reminder_due', 
        search='_search_is_reminder_due'
    )
    has_pending_request = fields.Boolean(
        string='Has Pending Request', 
        compute='_compute_has_pending_request'
    )

    @api.depends('last_recurring_date', 'interval_number', 'interval_unit', 'reminder_lead_days')
    def _compute_recurring_dates(self):
        for rec in self:
            if rec.last_recurring_date and rec.interval_number > 0:
                if rec.interval_unit == 'month':
                    due = rec.last_recurring_date + relativedelta(months=rec.interval_number)
                else:
                    due = rec.last_recurring_date + relativedelta(years=rec.interval_number)
                rec.next_due_date = due
                rec.reminder_date = due - relativedelta(days=rec.reminder_lead_days or 0)
            else:
                rec.next_due_date = False
                rec.reminder_date = False

    def _compute_has_pending_request(self):
        Request = self.env['benefit.request']
        for rec in self:
            # Check if there is an active draft or checked request for this definition
            pending = Request.search_count([
                ('benefit_definition_id', '=', rec.id),
                ('state', 'in', ['draft', 'checked'])
            ])
            rec.has_pending_request = pending > 0

    def _compute_is_reminder_due(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec._compute_has_pending_request()
            if rec.active and rec.reminder_date and not rec.has_pending_request:
                rec.is_reminder_due = (today >= rec.reminder_date)
            else:
                rec.is_reminder_due = False

    def _search_is_reminder_due(self, operator, value):
        today = fields.Date.context_today(self)
        # Find active definitions that reached their trigger date and don't have a pending request
        definitions = self.search([('active', '=', True), ('reminder_date', '!=', False)])
        
        due_ids = []
        for d in definitions:
            pending = self.env['benefit.request'].search_count([
                ('benefit_definition_id', '=', d.id),
                ('state', 'in', ['draft', 'checked'])
            ])
            if not pending and today >= d.reminder_date:
                due_ids.append(d.id)
                
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', due_ids)]
        else:
            return [('id', 'not in', due_ids)]

    def action_initiate_request(self):
        """ 🌟 One-click action to create and open a pre-filled Benefit Request """
        self.ensure_one()
        return {
            'name': _('Initiate Benefit Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'benefit.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_benefit_definition_id': self.id,
                'default_amount': self.amount,
                'default_note': _('Recurring renewal for cycle expiring on: %s') % (self.next_due_date or fields.Date.context_today(self)),
            }
        }