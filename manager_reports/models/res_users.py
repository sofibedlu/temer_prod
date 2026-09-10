# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    managerial_dashboard_access = fields.Selection(
        [
            ('none', 'No Access'),
            ('dashboard', 'Managerial Dashboard'),
            ('full', 'Managerial Dashboard + Weekly Reports'),
        ],
        string='Managerial Dashboard',
        default='none',
        compute='_compute_managerial_dashboard_access',
        inverse='_inverse_managerial_dashboard_access',
        store=False,
        help='Access level for Managerial Dashboard reports. Use this selection instead of the checkboxes below.',
    )

    @api.depends('groups_id')
    def _compute_managerial_dashboard_access(self):
        group_dashboard = self.env.ref('manager_reports.group_manager_reports', raise_if_not_found=False)
        group_weekly = self.env.ref('manager_reports.group_weekly_reports', raise_if_not_found=False)
        for user in self:
            try:
                if not group_dashboard or not group_weekly:
                    user.managerial_dashboard_access = 'none'
                    continue
                has_dashboard = group_dashboard in user.groups_id
                has_weekly = group_weekly in user.groups_id
                if has_dashboard and has_weekly:
                    user.managerial_dashboard_access = 'full'
                elif has_dashboard:
                    user.managerial_dashboard_access = 'dashboard'
                else:
                    user.managerial_dashboard_access = 'none'
            except Exception as e:
                _logger.warning('manager_reports: _compute_managerial_dashboard_access for user %s: %s', user.id, e)
                user.managerial_dashboard_access = 'none'

    def _inverse_managerial_dashboard_access(self):
        group_dashboard = self.env.ref('manager_reports.group_manager_reports', raise_if_not_found=False)
        group_weekly = self.env.ref('manager_reports.group_weekly_reports', raise_if_not_found=False)
        if not group_dashboard or not group_weekly:
            return
        for user in self:
            try:
                new_val = user.managerial_dashboard_access
                if new_val == 'full':
                    group_dashboard.sudo().write({'users': [(4, user.id)]})
                    group_weekly.sudo().write({'users': [(4, user.id)]})
                elif new_val == 'dashboard':
                    group_dashboard.sudo().write({'users': [(4, user.id)]})
                    group_weekly.sudo().write({'users': [(3, user.id)]})
                else:
                    group_dashboard.sudo().write({'users': [(3, user.id)]})
                    group_weekly.sudo().write({'users': [(3, user.id)]})
            except Exception as e:
                _logger.warning('manager_reports: _inverse_managerial_dashboard_access for user %s: %s', user.id, e)
