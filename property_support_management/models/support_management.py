from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class SupportManagement(models.Model):
    _name = 'support.management'
    _description = 'Job Order / Support Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Job Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    location_ids = fields.Many2many('support.location', string='Site / Office Location', tracking=True)
    date = fields.Datetime(string='Assignment Date', default=fields.Datetime.now, tracking=True, required=True)
    description = fields.Text(string='Description', tracking=True, required=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)

    assigned_to = fields.Many2many('res.users', string='Assigned To', tracking=True,
                                   domain=lambda self: [('id', 'in', self.env['support.team.config'].search([]).mapped('user_id.id'))])
    contact_ids = fields.Many2many('support.contact', string='Person of Contact', tracking=True)

    category_ids = fields.Many2many('support.category', string='Category', tracking=True)
    department_ids = fields.Many2many('support.department', string='Department', tracking=True)
    task_count = fields.Integer(string='Task #', default=1, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True)
    
    due_date = fields.Date(string='Due Date', tracking=True, required=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)

    status = fields.Selection([
        ('assigned', 'Assigned'),
        ('on_progress', 'On Progress'),
        ('completed', 'Completed'),
        ('not_completed', 'Not Completed')
    ], string='Status', default='assigned', required=True, tracking=True)

    is_completed = fields.Boolean(string='Completed', tracking=True)
    is_not_completed = fields.Boolean(string='Not Completed', tracking=True)
    is_manager = fields.Boolean(compute='_compute_is_manager', default=lambda self: self.env.user.has_group('property_support_management.group_support_manager'))
    is_assignee = fields.Boolean(compute='_compute_is_assignee')

    @api.onchange('date')
    def _onchange_assignment_date(self):
        if self.date:
            curr_date = self.date.date()
            today = fields.Date.context_today(self)
            if curr_date != today:
                self.date = datetime.combine(curr_date, datetime.min.time())

    @api.constrains(
        'category_ids', 'department_ids', 'location_ids',
        'contact_ids', 'assigned_to', 'task_count'
    )
    def _check_required_fields(self):
        for rec in self:
            if not rec.category_ids:
                raise UserError(_("Category is required."))
            if not rec.department_ids:
                raise UserError(_("Department is required."))
            if not rec.location_ids:
                raise UserError(_("Site / Office Location is required."))
            if not rec.contact_ids:
                raise UserError(_("Person of Contact is required."))
            if not rec.assigned_to:
                raise UserError(_("Assigned To is required."))
            if rec.task_count < 1:
                raise UserError(_("Task # must be at least 1."))

    @api.depends('due_date', 'status', 'completion_date')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.due_date:
                if record.status in ['completed', 'not_completed'] and record.completion_date:
                    record.is_overdue = record.completion_date.date() > record.due_date
                else:
                    record.is_overdue = today > record.due_date
            else:
                record.is_overdue = False
    
    def _compute_is_assignee(self):
        for record in self:
            record.is_assignee = self.env.user in record.assigned_to
    
    work_update = fields.Text(string='Work Update')
    update_ids = fields.One2many('support.management.update', 'support_id', string='Work Updates')
    additional_task_ids = fields.One2many('support.additional.task', 'support_id', string='Additional Tasks')
    achievement_ids = fields.One2many('support.management.achievement', 'support_id', string='Main Achievements')
    achievement_summary = fields.Html(
        string='Main Achievements', compute='_compute_achievement_summary', store=False)

    @api.depends('achievement_ids', 'achievement_ids.text')
    def _compute_achievement_summary(self):
        for rec in self:
            if rec.achievement_ids:
                lines = ''.join(
                    f'<li style="font-weight:bold; margin-bottom:4px;">&#x2022; {a.text}</li>'
                    for a in rec.achievement_ids if a.text
                )
                rec.achievement_summary = f'<ul style="padding-left:0; list-style:none;">{lines}</ul>'
            else:
                rec.achievement_summary = False

    # Reporting Fields
    assigned_date = fields.Datetime(string='Start Date', related='date', store=True, tracking=True)
    completion_date = fields.Datetime(string='Completion Date', tracking=True)
    time_taken = fields.Char(string='Time Taken', compute='_compute_time_taken', store=True)

    @api.depends('date', 'completion_date')
    def _compute_time_taken(self):
        for record in self:
            if record.date and record.completion_date:
                diff = record.completion_date - record.date
                days = diff.days
                hours, remainder = divmod(diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                record.time_taken = f"{days}d {hours}h {minutes}m"
            else:
                record.time_taken = False

    def _compute_is_manager(self):
        for record in self:
            record.is_manager = self.env.user.has_group('property_support_management.group_support_manager')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('support.management.seq') or _('New')
            if 'work_update' in vals:
                vals.pop('work_update')
        records = super(SupportManagement, self).create(vals_list)
        return records

    def write(self, vals):
        work_update = vals.get('work_update')
        if work_update:
            vals['work_update'] = False 

        is_manager = self.env.user.has_group('property_support_management.group_support_manager')
        
        assigning_new = 'assigned_to' in vals
        explicit_not_comp_in_vals = 'is_not_completed' in vals
        explicit_not_comp = vals.get('is_not_completed')

        if 'is_completed' in vals:
            is_comp = vals.get('is_completed')
            for record in self:
                # Permission check: Only manager can convert True -> False
                if record.is_completed and not is_comp and not is_manager:
                    raise UserError(_("Only a manager can convert a completed task back to on progress."))
                
                # If marking as completed, set status
                if is_comp and record.status != 'completed':
                    vals['status'] = 'completed'
                    vals['is_not_completed'] = False
                # If reopening (as manager), set status back
                elif not is_comp and record.status == 'completed' and is_manager:
                    vals['status'] = 'on_progress'

        if explicit_not_comp_in_vals:
            for record in self:
                if record.is_not_completed and not explicit_not_comp and not is_manager:
                    raise UserError(_("Only a manager can uncheck 'Not Completed'."))

                if explicit_not_comp and record.status != 'not_completed':
                    vals['status'] = 'not_completed'
                    vals['is_completed'] = False
                    # Create history tracking entries for all current assignees
                    for user in record.assigned_to:
                        self.env['support.management.history'].create({
                            'support_id': record.id,
                            'user_id': user.id,
                            'description': record.description,
                        })
                elif not explicit_not_comp and record.status == 'not_completed' and is_manager:
                    vals['status'] = 'on_progress'
                    # Remove the history since it was explicitly unchecked
                    history_records = self.env['support.management.history'].search([('support_id', '=', record.id)])
                    history_records.unlink()

        if assigning_new:
            for record in self:
                # If it's in not_completed state and being reassigned, log old history if needed, then move back
                if record.status == 'not_completed':
                    vals['status'] = 'assigned'
                    vals['is_not_completed'] = False

        if work_update and 'status' not in vals:
            for record in self:
                if record.status == 'assigned':
                    vals['status'] = 'on_progress'

        if work_update:
            vals['work_update'] = False

        for record in self:
            current_status = vals.get('status', record.status)
            if current_status == 'completed' and not record.completion_date:
                vals['completion_date'] = fields.Datetime.now()
            if current_status == 'on_progress' and record.status == 'completed':
                vals['completion_date'] = False

            if work_update:
                self.env['support.management.update'].create({
                    'support_id': record.id,
                    'description': work_update,
                })
                record.message_post(body=_(f"Work Update: {work_update}"))

        return super(SupportManagement, self).write(vals)

    def action_open_report_wizard(self):
        if len(self) > 1:
            raise UserError(_("Please select only one task at a time to generate a Task Report."))
        self.ensure_one()
        if self.is_completed:
            raise UserError(_("You cannot send a report for a completed task."))
        return {
            'name': _('Task Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'support.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_support_id': self.id}
        }

    def action_open_additional_task_wizard(self):
        self.ensure_one()
        return {
            'name': _('Additional Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'support.additional.task.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_support_id': self.id}
        }

class SupportManagementUpdate(models.Model):
    _name = 'support.management.update'
    _description = 'Work Update'
    _order = 'id desc'

    support_id = fields.Many2one('support.management', string='Support Job', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    description = fields.Text(string='Update Details', required=True)
