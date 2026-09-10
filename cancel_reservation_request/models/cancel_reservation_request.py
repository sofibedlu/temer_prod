from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CancelReservationRequest(models.Model):
    _name = 'property.reservation.cancel.request'
    _description = 'Reservation Cancel Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reservation_id'
    _order = 'create_date desc'

    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        required=True,
        readonly=True,
        tracking=True,
    )
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='reservation_id.property_id',
        store=True,
        readonly=True,
    )
    reservation_type_id = fields.Many2one(
        'property.reservation.configuration',
        string='Reservation Type',
        related='reservation_id.reservation_type_id',
        store=True,
        readonly=True,
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        related='reservation_id.salesperson_ids',
        store=True,
        readonly=True,
    )
    supervisor_id = fields.Many2one(
        'property.sales.supervisor',
        string='Sales Supervisor',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    supervisor_user_id = fields.Many2one(
        'res.users',
        string='Supervisor User',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    team_id = fields.Many2one(
        'property.sales.team',
        string='Sales Team',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    team_manager_id = fields.Many2one(
        'res.users',
        string='Team Manager',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    wing_id = fields.Many2one(
        'property.sales.wing',
        string='Wing',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    wing_manager_id = fields.Many2one(
        'res.users',
        string='Wing Manager',
        compute='_compute_sales_hierarchy',
        store=True,
        readonly=True,
    )
    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
    )
    reason_id = fields.Many2one(
        'property.sale.cancel.reason',
        string='Reason',
        readonly=True,
        tracking=True,
    )
    other = fields.Boolean(string='Other Reason', readonly=True)
    reason = fields.Text(string='Other Reason', readonly=True, tracking=True)
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        compute='_compute_cancel_reason',
        store=True,
    )
    state = fields.Selection(
        [
            ('prepare', 'Prepare'),
            ('check', 'Check'),
            ('approve', 'Approve'),
        ],
        default='prepare',
        string='Status',
        required=True,
        tracking=True,
    )
    checked_by_id = fields.Many2one('res.users', string='Checked By', readonly=True)
    checked_date = fields.Datetime(string='Checked Date', readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    can_check = fields.Boolean(compute='_compute_action_permissions')
    can_approve = fields.Boolean(compute='_compute_action_permissions')

    @api.depends('reservation_id.payment_line_ids.amount')
    def _compute_amount(self):
        for request in self:
            request.amount = sum(request.reservation_id.payment_line_ids.mapped('amount'))

    @api.depends(
        'reservation_id',
        'reservation_id.salesperson_ids',
        'reservation_id.supervisor_id',
        'reservation_id.team_id',
        'reservation_id.wing_id',
    )
    def _compute_sales_hierarchy(self):
        for request in self:
            reservation = request.reservation_id
            salesperson = reservation.salesperson_ids
            supervisor = reservation.supervisor_id
            team = reservation.team_id
            wing = reservation.wing_id

            if salesperson and not (supervisor and team and wing):
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', salesperson.id)
                ], limit=1)
                if mapping and mapping.supervisor_id:
                    supervisor = supervisor or mapping.supervisor_id
                    team = team or self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', supervisor.id)
                    ], limit=1)
                    if team:
                        wing = wing or self.env['property.sales.wing'].search([
                            ('team_ids', 'in', team.id)
                        ], limit=1)
                else:
                    supervisor = supervisor or self.env['property.sales.supervisor'].search([
                        ('name', '=', salesperson.id)
                    ], limit=1)
                    if supervisor:
                        team = team or self.env['property.sales.team'].search([
                            ('supervisor_ids', 'in', supervisor.id)
                        ], limit=1)
                        if team:
                            wing = wing or self.env['property.sales.wing'].search([
                                ('team_ids', 'in', team.id)
                            ], limit=1)
                    else:
                        team = team or self.env['property.sales.team'].search([
                            ('manager_id', '=', salesperson.id)
                        ], limit=1)
                        if team:
                            wing = wing or self.env['property.sales.wing'].search([
                                ('team_ids', 'in', team.id)
                            ], limit=1)
                        if not wing:
                            wing = self.env['property.sales.wing'].search([
                                ('manager_id', '=', salesperson.id)
                            ], limit=1)

            request.supervisor_id = supervisor
            request.supervisor_user_id = supervisor.name if supervisor else False
            request.team_id = team
            request.team_manager_id = team.manager_id if team else False
            request.wing_id = wing
            request.wing_manager_id = wing.manager_id if wing else False

    @api.depends('other', 'reason', 'reason_id.name')
    def _compute_cancel_reason(self):
        for request in self:
            request.cancel_reason = request.reason if request.other else request.reason_id.name

    def _compute_action_permissions(self):
        can_check = self.env.user.has_group(
            'cancel_reservation_request.group_cancel_reservation_request_manager'
        )
        can_approve = self.env.user.has_group(
            'cancel_reservation_request.group_cancel_reservation_request_approver'
        )
        for request in self:
            request.can_check = can_check
            request.can_approve = can_approve

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            request._post_reservation_log(
                _('Cancel request created with reason: %s') % request.cancel_reason
            )
        return requests

    @api.constrains('reservation_id', 'state')
    def _check_active_request(self):
        for request in self:
            if request.state == 'approve':
                continue
            domain = [
                ('id', '!=', request.id),
                ('reservation_id', '=', request.reservation_id.id),
                ('state', 'in', ['prepare', 'check']),
            ]
            if self.search_count(domain):
                raise ValidationError(_('This reservation already has a pending cancel request.'))

    def action_check(self):
        if not self.env.user.has_group('cancel_reservation_request.group_cancel_reservation_request_manager'):
            raise ValidationError(_('Only a cancel reservation manager can check this request.'))
        for request in self:
            if request.state != 'prepare':
                raise ValidationError(_('Only prepared requests can be checked.'))
            request._check_reservation_is_reserved()
            request.write({
                'state': 'check',
                'checked_by_id': self.env.user.id,
                'checked_date': fields.Datetime.now(),
            })
            request._post_reservation_log(
                _('Cancel request checked by %s') % self.env.user.name
            )

    def action_approve(self):
        if not self.env.user.has_group('cancel_reservation_request.group_cancel_reservation_request_approver'):
            raise ValidationError(_('Only a cancel reservation approver can approve this request.'))
        for request in self:
            if request.state != 'check':
                raise ValidationError(_('Only checked requests can be approved.'))
            request._check_reservation_is_reserved()
            request._cancel_reservation()
            request.write({
                'state': 'approve',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            request._post_reservation_log(
                _('Cancel request approved by %s') % self.env.user.name
            )

    def _post_reservation_log(self, body):
        for request in self:
            if request.reservation_id:
                request.reservation_id.message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

    def _check_reservation_is_reserved(self):
        for request in self:
            if request.reservation_id.status != 'reserved':
                raise ValidationError(_(
                    "Cancel request can only be checked or approved when the reservation is Reserved. "
                    "Current reservation status is %s."
                ) % (request.reservation_id.status or _('unknown')))

    def _cancel_reservation(self):
        for request in self:
            reservation = request.reservation_id
            if reservation.reservation_type_id.reservation_type == 'quick':
                raise ValidationError(_('Quick reservations must use the direct cancel button.'))
            previous_status = reservation.status
            reservation.write({
                'status': 'canceled',
                'canceled_time': fields.Datetime.now(),
                'canceled_reason': request.cancel_reason,
            })
            if previous_status == 'reserved':
                reservation.property_id.sudo().write({'state': 'available'})

            stage = self.env['crm.stage'].search([('name', 'ilike', 'Follow Up')], limit=1)
            if stage and reservation.crm_lead_id:
                reservation.crm_lead_id.sudo().write({'stage_id': stage.id})
            temer_lead = reservation.sudo().temer_lead_ids
            if temer_lead:
                temer_lead.sudo().write({'state': 'follow_up'})
