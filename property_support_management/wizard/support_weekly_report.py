from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SupportWeeklyReportWizard(models.TransientModel):
    _name = 'support.weekly.report.wizard'
    _description = 'Weekly Support Report Wizard'

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    assignee_id = fields.Many2one('res.users', string='Assignee', required=True, default=lambda self: self.env.user,
                                  domain=lambda self: [('id', 'in', self.env['support.team.config'].search([]).mapped('user_id.id'))])
    department = fields.Char(string='Department', default='IT')
    is_manager = fields.Boolean(default=lambda self: self.env.user.has_group('property_support_management.group_support_manager'))

    section_ids = fields.One2many('support.weekly.report.section', 'wizard_id', string='Report Sections')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'section_ids' in fields_list and not res.get('section_ids'):
            res['section_ids'] = [
                (0, 0, {
                    'sequence': 10,
                    'title': '1. Executive Summary',
                    'line_ids': [(0, 0, {
                        'sequence': 10,
                        'line_type': 'paragraph',
                        'text': 'During this period, the IT Support team played a critical role in maintaining the continuity and efficiency of daily operations.',
                    })]
                }),
            ]
        return res

    def _get_tasks_in_period(self):
        """Return all support.management tasks in the period (bypasses record rules)."""
        self.ensure_one()
        from datetime import datetime, time
        start_dt = datetime.combine(self.start_date, time.min)
        end_dt = datetime.combine(self.end_date, time.max)
        domain = [
            ('date', '>=', start_dt),
            ('date', '<=', end_dt),
            ('assigned_to', 'in', self.assignee_id.id),
            ('status', '!=', 'not_completed'),
        ]
        return self.env['support.management'].sudo().search(domain, order='date asc')

    def get_support_operations(self):
        """Fetch support tasks formatted for the operations table."""
        tasks = self._get_tasks_in_period()
        operations = []
        for task in tasks:
            time_taken_val = task.time_taken
            if not time_taken_val and task.status in ['assigned', 'on_progress'] and task.date:
                diff = fields.Datetime.now() - task.date
                days = diff.days
                hours, remainder = divmod(diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                time_taken_val = f"{days}d {hours}h {minutes}m"

            operations.append({
                'category': ', '.join(task.category_ids.mapped('name')) if task.category_ids else '—',
                'site': ', '.join(task.location_ids.mapped('name')) if task.location_ids else '—',
                'department': ', '.join(task.department_ids.mapped('name')) if task.department_ids else '—',
                'remark': task.description or '—',
                'task_count': task.task_count or 0,
                'status': dict(task._fields['status'].selection).get(task.status, ''),
                'date': task.date.strftime('%b %d') if task.date else '—',
                'time_taken': time_taken_val or '—',
                'is_overdue': task.is_overdue,
            })
            for add_task in task.additional_task_ids.filtered('is_confirmed'):
                operations.append({
                    'category': ', '.join(add_task.category_ids.mapped('name')) if add_task.category_ids else '—',
                    'site': ', '.join(add_task.location_ids.mapped('name')) if add_task.location_ids else '—',
                    'department': ', '.join(add_task.department_ids.mapped('name')) if add_task.department_ids else '—',
                    'remark': add_task.description or '—',
                    'task_count': add_task.task_count or 0,
                    'status': dict(task._fields['status'].selection).get(task.status, ''),
                    'date': add_task.date.strftime('%b %d') if add_task.date else '—',
                    'time_taken': time_taken_val or '—',
                    'is_overdue': task.is_overdue,
                })
        return operations

    def get_category_summary(self):
        """Sum task_count per category across all tasks in the period."""
        tasks = self._get_tasks_in_period()
        category_counts = {}
        total = 0
        for task in tasks:
            count = task.task_count or 0
            for cat in task.category_ids:
                category_counts[cat.name] = category_counts.get(cat.name, 0) + count
                total += count
            for add_task in task.additional_task_ids.filtered('is_confirmed'):
                add_count = add_task.task_count or 0
                for cat in add_task.category_ids:
                    category_counts[cat.name] = category_counts.get(cat.name, 0) + add_count
                    total += add_count
        rows = sorted(category_counts.items(), key=lambda x: x[0])
        return {
            'rows': [{'name': name, 'count': count} for name, count in rows],
            'total': total,
        }

    def action_generate_report(self):
        self.ensure_one()
        if self.start_date > self.end_date:
            raise UserError(_("Start Date cannot be after End Date."))
        return self.env.ref(
            'property_support_management.action_report_weekly_support'
        ).report_action(self)


class SupportWeeklyReportSection(models.TransientModel):
    _name = 'support.weekly.report.section'
    _description = 'Weekly Support Report Section'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('support.weekly.report.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    title = fields.Char(string='Section Title', required=True)
    line_ids = fields.One2many('support.weekly.report.line', 'section_id', string='Description Lines')


class SupportWeeklyReportLine(models.TransientModel):
    _name = 'support.weekly.report.line'
    _description = 'Report Section Description Line'
    _order = 'sequence, id'

    section_id = fields.Many2one('support.weekly.report.section', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    line_type = fields.Selection([
        ('paragraph', 'Paragraph'),
        ('bullet', '• Bullet'),
        ('numbered', 'Numbered'),
    ], string='Type', default='paragraph', required=True)
    # Text field allows multi-line. For bullets/numbered, each line in the text becomes its own item.
    text = fields.Text(string='Description', required=True)
