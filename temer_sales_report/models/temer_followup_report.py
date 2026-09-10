from odoo import models, fields, api

from .temer_report_export import temer_export_act_url


SHORT_MONTH = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec',
}


class TemerLeadFollowupReport(models.Model):
    """
    Extend temer.lead.followup with report fields.
    Wing and supervisor are resolved from user_id via the salesperson mapping,
    falling back to the lead's stored values if available.
    """
    _inherit = 'temer.lead.followup'

    def action_temer_export_office_visit(self):
        return temer_export_act_url(
            self,
            'office_visit',
            [('activity_type', '=', 'office_visit')],
        )

    def action_temer_export_site_visit(self):
        return temer_export_act_url(
            self,
            'site_visit',
            [('activity_type', '=', 'site_visit')],
        )

    report_wing_id = fields.Many2one(
        'property.sales.wing',
        string='Wing Name',
        compute='_compute_followup_hierarchy',
        store=False,
    )
    report_supervisor_id = fields.Many2one(
        'property.sales.supervisor',
        string='Sales Supervisor',
        compute='_compute_followup_hierarchy',
        store=False,
    )
    report_wing_display = fields.Char(
        string='Wing Name',
        compute='_compute_followup_hierarchy',
        store=False,
    )
    report_supervisor_display = fields.Char(
        string='Sales Supervisor',
        compute='_compute_followup_hierarchy',
        store=False,
    )
    # NOT stored — always computed fresh from activity_date
    report_date_display = fields.Char(
        string='Date',
        compute='_compute_followup_date_display',
        store=False,
    )

    @api.depends('activity_date')
    def _compute_followup_date_display(self):
        for rec in self:
            if rec.activity_date:
                d = rec.activity_date.date()
                rec.report_date_display = '{}-{}-{}'.format(
                    d.day, SHORT_MONTH.get(d.month, ''), d.year
                )
            else:
                rec.report_date_display = ''

    @api.depends('user_id', 'lead_id', 'lead_id.wing_id', 'lead_id.supervisor_id')
    def _compute_followup_hierarchy(self):
        """
        Resolve wing and supervisor for each followup activity.
        Priority:
        1. lead_id.wing_id / lead_id.supervisor_id if already set on the lead
        2. Look up from user_id via property.salesperson.mapping
        """
        for rec in self:
            wing = False
            supervisor = False

            # Priority 1: use what's stored on the lead
            if rec.lead_id:
                if rec.lead_id.wing_id:
                    wing = rec.lead_id.wing_id
                if rec.lead_id.supervisor_id:
                    supervisor = rec.lead_id.supervisor_id

            # Priority 2: look up from user_id if still empty
            user_id = rec.user_id.id if rec.user_id else False
            if user_id and (not wing or not supervisor):
                mapping = self.env['property.salesperson.mapping'].search(
                    [('user_id', '=', user_id)], limit=1
                )
                if mapping and mapping.supervisor_id:
                    if not supervisor:
                        supervisor = mapping.supervisor_id
                    if not wing:
                        team = self.env['property.sales.team'].search(
                            [('supervisor_ids', 'in', mapping.supervisor_id.id)], limit=1
                        )
                        if team:
                            wing = self.env['property.sales.wing'].search(
                                [('team_ids', 'in', team.id)], limit=1
                            )
                elif not supervisor:
                    # Maybe user is a supervisor themselves
                    sup_rec = self.env['property.sales.supervisor'].search(
                        [('name', '=', user_id)], limit=1
                    )
                    if sup_rec:
                        supervisor = sup_rec
                        if not wing:
                            wing = sup_rec.sales_team_id.wing_id
                    else:
                        # Check if user is a team manager
                        if not wing:
                            team = self.env['property.sales.team'].search(
                                [('manager_id', '=', user_id)], limit=1
                            )
                            if team:
                                wing = self.env['property.sales.wing'].search(
                                    [('team_ids', 'in', team.id)], limit=1
                                )
                        # Check if user is a wing manager
                        if not wing:
                            wing = self.env['property.sales.wing'].search(
                                [('manager_id', '=', user_id)], limit=1
                            )

            rec.report_supervisor_id = supervisor
            rec.report_wing_id = wing
            rec.report_supervisor_display = supervisor.name.name if supervisor and supervisor.name else '-'
            rec.report_wing_display = wing.name if wing else '-'
