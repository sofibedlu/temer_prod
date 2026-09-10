from odoo import models, fields, api

from .temer_report_export import SALES_DEAL_CLOSED_DOMAIN, temer_export_act_url


def _gregorian_to_ethiopian_year(date):
    """Ethiopian year from Gregorian date. New Year ~Sep 11."""
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


class PropertySaleReport(models.Model):
    _inherit = 'property.sale'

    def action_temer_export_sales_deal_closed(self):
        return temer_export_act_url(
            self,
            'sales_deal_closed',
            SALES_DEAL_CLOSED_DOMAIN,
        )

    # ── Sales hierarchy ───────────────────────────────────────────────────────

    report_supervisor_id = fields.Many2one(
        'property.sales.supervisor',
        string='Sales Supervisor',
        compute='_compute_report_hierarchy',
        store=False,
    )
    report_wing_id = fields.Many2one(
        'property.sales.wing',
        string='Wing Name',
        compute='_compute_report_hierarchy',
        store=False,
    )
    # Char display fields — show "-" when no value
    report_supervisor_display = fields.Char(
        string='Sales Supervisor',
        compute='_compute_report_hierarchy',
        store=False,
    )
    report_wing_display = fields.Char(
        string='Wing Name',
        compute='_compute_report_hierarchy',
        store=False,
    )

    # ── Fiscal year as Char (no comma formatting) ─────────────────────────────

    report_fiscal_year = fields.Char(
        string='Fiscal Year',
        compute='_compute_report_date_fields',
        store=False,
    )
    report_period = fields.Char(
        string='Period',
        compute='_compute_report_date_fields',
        store=False,
    )
    # Date formatted as "10-Apr-2026" — NOT stored, always computed fresh from order_date
    report_date_display = fields.Char(
        string='Date',
        compute='_compute_report_date_fields',
        store=False,
    )

    # ── Stored fields for search/group-by (property type and bedroom) ─────────
    # These are stored so they can be used in search domains and group-by

    report_property_type_stored = fields.Selection(
        related='property_id.property_type',
        string='Property Type',
        store=True,
    )
    report_bedroom_stored = fields.Integer(
        related='property_id.bedroom',
        string='Bedrooms',
        store=True,
    )
    report_property_is_legacy = fields.Boolean(
        related='property_id.is_legacy',
        string='Is Legacy Property',
        store=True,
        readonly=True,
    )

    # ── Property type display ─────────────────────────────────────────────────

    report_property_type = fields.Char(
        string='Property Type',
        compute='_compute_report_unit_type',
        store=False,
    )

    # ── Unit type display ─────────────────────────────────────────────────────

    report_unit_type = fields.Char(
        string='Unit Type',
        compute='_compute_report_unit_type',
        store=False,
    )

    # ── Gross/Net area (stored related so they work in tree views) ────────────

    report_gross_area = fields.Float(
        string='Gross Area',
        related='property_id.gross_area',
        store=False,
    )
    report_net_area = fields.Float(
        string='Net Area',
        related='property_id.net_area',
        store=False,
    )

    # ── Cash collection ───────────────────────────────────────────────────────

    report_cash_collection = fields.Monetary(
        string='Cash Collection',
        compute='_compute_report_cash_collection',
        store=False,
        currency_field='currency_id',
    )

    # ── Compute methods ───────────────────────────────────────────────────────

    @api.depends('reservation_id', 'sales_person')
    def _compute_report_hierarchy(self):
        for rec in self:
            supervisor = False
            wing = False
            salesperson_user = False

            if rec.sales_person:
                salesperson_user = rec.sales_person
            elif rec.reservation_id and rec.reservation_id.salesperson_ids:
                salesperson_user = rec.reservation_id.salesperson_ids

            if salesperson_user:
                mapping = self.env['property.salesperson.mapping'].search(
                    [('user_id', '=', salesperson_user.id)], limit=1
                )
                if mapping and mapping.supervisor_id:
                    supervisor = mapping.supervisor_id
                    team = self.env['property.sales.team'].search(
                        [('supervisor_ids', 'in', supervisor.id)], limit=1
                    )
                    if team:
                        wing_rec = self.env['property.sales.wing'].search(
                            [('team_ids', 'in', team.id)], limit=1
                        )
                        wing = wing_rec
                else:
                    # Check if user is a supervisor
                    sup_rec = self.env['property.sales.supervisor'].search(
                        [('name', '=', salesperson_user.id)], limit=1
                    )
                    if sup_rec:
                        supervisor = sup_rec
                        wing = sup_rec.sales_team_id.wing_id if sup_rec.sales_team_id else False
                    else:
                        # Check if user is a team manager
                        team = self.env['property.sales.team'].search(
                            [('manager_id', '=', salesperson_user.id)], limit=1
                        )
                        if team:
                            wing = self.env['property.sales.wing'].search(
                                [('team_ids', 'in', team.id)], limit=1
                            )
                        else:
                            # Check if user is a wing manager
                            wing = self.env['property.sales.wing'].search(
                                [('manager_id', '=', salesperson_user.id)], limit=1
                            )

            rec.report_supervisor_id = supervisor
            rec.report_wing_id = wing
            rec.report_supervisor_display = supervisor.name.name if supervisor and supervisor.name else '-'
            rec.report_wing_display = wing.name if wing else '-'

    @api.depends('order_date')
    def _compute_report_date_fields(self):
        for rec in self:
            if rec.order_date:
                eth_year = _gregorian_to_ethiopian_year(rec.order_date)
                rec.report_fiscal_year = str(eth_year) if eth_year else ''
                rec.report_period = MONTH_NAMES.get(rec.order_date.month, '')
                # Format: "10-Apr-2026"
                rec.report_date_display = '{}-{}-{}'.format(
                    rec.order_date.day,
                    SHORT_MONTH.get(rec.order_date.month, ''),
                    rec.order_date.year
                )
            else:
                rec.report_fiscal_year = ''
                rec.report_period = ''
                rec.report_date_display = ''

    @api.depends('property_id', 'property_id.property_type', 'property_id.bedroom',
                 'property_id.property_type_id')
    def _compute_report_unit_type(self):
        for rec in self:
            prop = rec.property_id
            if not prop:
                rec.report_property_type = '-'
                rec.report_unit_type = '-'
            else:
                ptype = prop.property_type or ''
                rec.report_property_type = ptype.capitalize() if ptype else '-'
                if ptype == 'commercial':
                    rec.report_unit_type = '0'
                else:
                    bedrooms = prop.bedroom or 0
                    rec.report_unit_type = '{}BR'.format(bedrooms) if bedrooms else '-'

    @api.depends(
        'collection_order_id',
        'collection_order_id.amount_collected',
        'reservation_id',
        'reservation_id.payment_line_ids.amount',
        'reservation_id.payment_line_ids.is_verifed',
    )
    def _compute_report_cash_collection(self):
        for rec in self:
            collection = rec.collection_order_id or self.env['collection.order'].search(
                [('sale_id', '=', rec.id)], limit=1,
            )
            collection_amount = collection.amount_collected if collection else 0.0

            advance_amount = 0.0
            if rec.reservation_id:
                payments = rec.reservation_id.payment_line_ids.filtered(
                    lambda p: p.payment_status != 'canceled' and p.is_verifed
                )
                advance_amount = sum(payments.mapped('amount'))

            rec.report_cash_collection = collection_amount + advance_amount
