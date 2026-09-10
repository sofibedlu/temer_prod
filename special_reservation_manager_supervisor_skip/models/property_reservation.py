# -*- coding: utf-8 -*-

from odoo import models, api


class PropertyReservationManagerSupervisorSkip(models.Model):
    _inherit = 'property.reservation'

    @api.model
    def _is_sales_or_wing_manager(self, user=None):
        """True when user is a sales team manager or wing manager in temer structure."""
        user = user or self.env.user
        if self.env['property.sales.team'].sudo().search_count(
            [('manager_id', '=', user.id)], limit=1
        ):
            return True
        if self.env['property.sales.wing'].sudo().search_count(
            [('manager_id', '=', user.id)], limit=1
        ):
            return True
        return False

    def _should_skip_supervisor_step(self):
        self.ensure_one()
        if self._is_sales_or_wing_manager():
            return True
        return bool(
            self.salesperson_ids
            and self._is_sales_or_wing_manager(self.salesperson_ids)
        )

    def _reset_manager_submitted_to_draft(self):
        """Managers stuck at Submitted cannot edit amount/duration — reopen in Draft."""
        for rec in self:
            if rec._should_skip_supervisor_step() and rec.state == 'submitted':
                rec.write({'state': 'draft'})

    def action_request_special_approval(self):
        self._reset_manager_submitted_to_draft()
        return super().action_request_special_approval()

    def action_view_special_approval(self):
        self._reset_manager_submitted_to_draft()
        return super().action_view_special_approval()
