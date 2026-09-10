import re

from odoo import models, fields, api

from .temer_report_export import temer_export_act_url


def _gregorian_to_ethiopian_year(date):
    if not date:
        return False
    if date.month < 9 or (date.month == 9 and date.day < 11):
        return date.year - 8
    return date.year - 7


MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December',
}

SHORT_MONTH = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec',
}


def _resolve_hierarchy(env, user_id):
    """
    Given a res.users id, return (supervisor_record, wing_record).
    Hierarchy lookup order:
      1. Salesperson → mapping → supervisor → team → wing
      2. User is a supervisor → their team's wing
      3. User is a team/sales manager → their wing
      4. User is a wing manager → that wing (no supervisor)
    Returns (supervisor or False, wing or False)
    """
    Sup = env['property.sales.supervisor']
    Wing = env['property.sales.wing']

    if not user_id:
        return False, False

    # Case 1: regular salesperson
    mapping = env['property.salesperson.mapping'].search(
        [('user_id', '=', user_id)], limit=1
    )
    if mapping and mapping.supervisor_id:
        supervisor = mapping.supervisor_id
        team = env['property.sales.team'].search(
            [('supervisor_ids', 'in', supervisor.id)], limit=1
        )
        wing = Wing.search([('team_ids', 'in', team.id)], limit=1) if team else False
        return supervisor, wing

    # Case 2: user is a supervisor
    sup_rec = Sup.search([('name', '=', user_id)], limit=1)
    if sup_rec:
        wing = sup_rec.sales_team_id.wing_id if sup_rec.sales_team_id else False
        return sup_rec, wing

    # Case 3: user is a team/sales manager
    team = env['property.sales.team'].search([('manager_id', '=', user_id)], limit=1)
    if team:
        wing = Wing.search([('team_ids', 'in', team.id)], limit=1)
        return False, wing  # no supervisor — they ARE the manager level

    # Case 4: user is a wing manager
    wing = Wing.search([('manager_id', '=', user_id)], limit=1)
    if wing:
        return False, wing  # no supervisor — they ARE the wing manager

    return False, False


class TemerLeadReport(models.Model):
    _inherit = 'temer.lead'

    # Odoo 17 read_group ORDER BY must use groupby fields or field:aggregate.
    _READ_GROUP_ORDER_AGGREGATE = {
        'state_sequence': 'min',
        'create_date': 'max',
        'write_date': 'max',
    }

    @api.model
    def _read_group_orderby(self, order, groupby_terms, query):
        if not order:
            return super()._read_group_orderby(order, groupby_terms, query)
        parts = []
        for order_part in order.split(','):
            order_part = order_part.strip()
            match = re.match(
                r'^(?P<field>[a-z0-9_]+)(?::(?P<func>[a-z_]+))?\s*(?P<direction>asc|desc)?$',
                order_part,
                re.I,
            )
            if match and not match.group('func'):
                field = match.group('field')
                if field not in groupby_terms and field in self._READ_GROUP_ORDER_AGGREGATE:
                    direction = (match.group('direction') or 'asc').lower()
                    agg = self._READ_GROUP_ORDER_AGGREGATE[field]
                    parts.append(f'{field}:{agg} {direction}')
                    continue
            parts.append(order_part)
        return super()._read_group_orderby(', '.join(parts), groupby_terms, query)

    def action_temer_export_lead_generated(self):
        return temer_export_act_url(self, 'lead_generated', [])

    def action_temer_export_follow_up(self):
        return temer_export_act_url(self, 'follow_up', [('state', '=', 'follow_up')])

    report_fiscal_year = fields.Char(
        string='Fiscal Year',
        compute='_compute_lead_report_date',
        store=False,
    )
    report_period = fields.Char(
        string='Period',
        compute='_compute_lead_report_date',
        store=False,
    )
    # NOT stored — always computed fresh from create_date
    report_date_display = fields.Char(
        string='Date',
        compute='_compute_lead_report_date',
        store=False,
    )

    # NOT stored — computed on the fly to avoid mass recompute
    report_supervisor_id = fields.Many2one(
        'property.sales.supervisor',
        string='Sales Supervisor',
        compute='_compute_lead_hierarchy',
        store=False,
    )
    report_wing_id = fields.Many2one(
        'property.sales.wing',
        string='Wing Name',
        compute='_compute_lead_hierarchy',
        store=False,
    )
    # Char fallback for display — shows "-" when no supervisor
    report_supervisor_display = fields.Char(
        string='Sales Supervisor',
        compute='_compute_lead_hierarchy',
        store=False,
    )
    report_wing_display = fields.Char(
        string='Wing Name',
        compute='_compute_lead_hierarchy',
        store=False,
    )

    @api.depends('create_date')
    def _compute_lead_report_date(self):
        for rec in self:
            if rec.create_date:
                d = rec.create_date.date()
                eth_year = _gregorian_to_ethiopian_year(d)
                rec.report_fiscal_year = str(eth_year) if eth_year else ''
                rec.report_period = MONTH_NAMES.get(d.month, '')
                rec.report_date_display = '{}-{}-{}'.format(
                    d.day, SHORT_MONTH.get(d.month, ''), d.year
                )
            else:
                rec.report_fiscal_year = ''
                rec.report_period = ''
                rec.report_date_display = ''

    @api.depends('supervisor_id', 'wing_id', 'user_id')
    def _compute_lead_hierarchy(self):
        for rec in self:
            # Use stored values first
            sup = rec.supervisor_id
            wing = rec.wing_id

            # Fall back to lookup from user_id
            if not sup and not wing:
                sup, wing = _resolve_hierarchy(self.env, rec.user_id.id if rec.user_id else False)
            elif not wing and rec.user_id:
                _, wing = _resolve_hierarchy(self.env, rec.user_id.id)
            elif not sup and rec.user_id:
                sup, _ = _resolve_hierarchy(self.env, rec.user_id.id)

            rec.report_supervisor_id = sup
            rec.report_wing_id = wing
            rec.report_supervisor_display = sup.name.name if sup and sup.name else '-'
            rec.report_wing_display = wing.name if wing else '-'
