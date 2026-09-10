from markupsafe import Markup
from datetime import timedelta
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class PropertyPreContractRefundDocumentType(models.Model):
    _name = 'property.pre.contract.refund.document.type'
    _description = 'Pre Contract Refund Document Label'
    _order = 'sequence, name'

    DOCUMENT_CODES = [
        ('application_letter', 'Application Letter'),
        ('crv', 'CRV'),
        ('deposit_slip_cpo', 'Deposit Slip / CPO'),
        ('id_copy', 'ID Copy'),
        ('other', 'Other'),
    ]

    name = fields.Char(string='Document Label', required=True)
    code = fields.Selection(
        DOCUMENT_CODES,
        string='Document Code',
        default='other',
        required=True,
    )
    sequence = fields.Integer(default=100)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'name_uniq',
            'unique(name)',
            'This document label already exists.',
        ),
    ]

    @api.model
    def name_create(self, name):
        label_name = (name or '').strip()
        if not label_name:
            raise ValidationError(_('Document label is required.'))
        existing = self.search([('name', '=ilike', label_name)], limit=1)
        if existing:
            return existing.name_get()[0]
        return self.create({'name': label_name, 'code': 'other'}).name_get()[0]


class PropertyPreContractRefundDocumentLine(models.Model):
    _name = 'property.pre.contract.refund.document.line'
    _description = 'Pre Contract Refund Required Document'
    _order = 'sequence, id'

    DOCUMENT_TYPES = [
        ('application_letter', 'Application Letter'),
        ('crv', 'CRV'),
        ('deposit_slip_cpo', 'Deposit Slip / CPO'),
        ('id_copy', 'ID Copy'),
        ('other', 'Other'),
    ]

    refund_id = fields.Many2one(
        'property.pre.contract.refund',
        string='Refund',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    document_label_id = fields.Many2one(
        'property.pre.contract.refund.document.type',
        string='Document Label',
        ondelete='restrict',
    )
    document_type = fields.Selection(
        DOCUMENT_TYPES,
        string='Document Code',
        required=True,
        default='other',
    )
    file = fields.Binary(
        string='File',
        attachment=True,
    )
    filename = fields.Char(string='Filename')
    note = fields.Char(string='Note')

    @api.onchange('document_label_id')
    def _onchange_document_label_id(self):
        if self.document_label_id:
            self.document_type = self.document_label_id.code or 'other'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            label_id = vals.get('document_label_id')
            if label_id and not vals.get('document_type'):
                label = self.env['property.pre.contract.refund.document.type'].browse(label_id)
                vals['document_type'] = label.code or 'other'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('document_label_id') and not vals.get('document_type'):
            label = self.env['property.pre.contract.refund.document.type'].browse(vals['document_label_id'])
            vals = dict(vals, document_type=label.code or 'other')
        return super().write(vals)

    def action_preview_file(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Please upload a file before previewing it.'))
        filename = quote(self.filename or self.document_label_id.display_name or 'document')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file/%s?download=false' % (
                self._name,
                self.id,
                filename,
            ),
            'target': 'new',
        }


class PropertyPreContractRefund(models.Model):
    _name = 'property.pre.contract.refund'
    _description = 'Pre Contract Refund'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
    )
    date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        domain=lambda self: [('id', 'in', self._get_reservation_partner_ids())],
    )
    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        required=True,
        tracking=True,
        domain=lambda self: self._get_reservation_domain(),
    )
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='reservation_id.property_id',
        store=True,
        readonly=True,
    )
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        related='reservation_id.site_id',
        store=True,
        readonly=True,
    )
    wing_name = fields.Char(
        string='Wing',
        compute='_compute_wing_name',
        readonly=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        related='reservation_id.salesperson_ids',
        store=True,
        readonly=True,
    )
    salesperson_name = fields.Char(
        string='Salesperson',
        related='reservation_id.salesperson_ids.name',
        store=True,
        readonly=True,
    )
    sales_officer_id = fields.Many2one(
        'res.users',
        string='Sales Officer',
        related='reservation_id.salesperson_ids',
        store=True,
        readonly=True,
    )
    sales_supervisor_name = fields.Char(
        string='Sales Supervisor',
        compute='_compute_sales_supervisor_name',
        store=True,
        readonly=True,
    )
    unit_details = fields.Char(
        string='Unit Details',
        compute='_compute_unit_and_payment_info',
        store=True,
        readonly=True,
    )
    original_payment_method = fields.Char(
        string='Original Payment Method',
        compute='_compute_unit_and_payment_info',
        store=True,
        readonly=True,
    )
    refund_type = fields.Selection(
        [
            ('full_cancellation', 'Full Cancellation'),
            ('overpayment', 'Overpayment'),
        ],
        string='Legacy Refund Type',
        default='full_cancellation',
        tracking=True,
    )
    refund_type_id = fields.Many2one(
        'property.pre.contract.refund.type',
        string='Refund Type',
        default=lambda self: self.env.ref(
            'pre_contract_refund.refund_type_full_cancellation',
            raise_if_not_found=False,
        ),
        ondelete='restrict',
        required=True,
        tracking=True,
    )
    refund_reason_id = fields.Many2one(
        'property.pre.contract.refund.reason',
        string='Refund Reason',
        ondelete='restrict',
        tracking=True,
    )
    refund_reason_other = fields.Char(
        string='Other Refund Reason',
        tracking=True,
    )
    is_other_refund_reason = fields.Boolean(
        string='Other Refund Reason Selected',
        compute='_compute_is_other_refund_reason',
        store=True,
    )
    actual_refund_reason = fields.Char(
        string='Actual Refund Reason',
        compute='_compute_actual_refund_reason',
        store=True,
        readonly=True,
    )
    refund_type_code = fields.Selection(
        related='refund_type_id.code',
        string='Refund Type Code',
        store=True,
        readonly=True,
    )
    payment_option = fields.Selection(
        [
            ('normal', 'Normal'),
            ('immediate', 'Immediate (Special)'),
        ],
        string='Payment Option',
        required=True,
        default='normal',
        tracking=True,
    )
    crv_required = fields.Boolean(
        string='CRV Required',
        compute='_compute_payment_flags',
        store=True,
    )
    is_cpo_crv_case = fields.Boolean(
        string='CPO + CRV Case',
        compute='_compute_payment_flags',
        store=True,
    )
    cpo_crv_originals_received = fields.Boolean(
        string='CPO and CRV Originals Received from Customer',
        tracking=True,
    )
    is_submitted = fields.Boolean(
        string='Submitted',
        default=False,
        copy=False,
    )
    crv_front_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Original CRV (Front)',
        copy=False,
    )
    crv_back_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Original CRV (Back)',
        copy=False,
    )
    application_letter_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Application Letter',
        copy=False,
    )
    deposit_slip_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Deposit Slip / CPO',
        copy=False,
    )
    id_copy_attachment_id = fields.Many2one(
        'ir.attachment',
        string='ID Copy',
        copy=False,
    )

    total_deposit_amount = fields.Monetary(
        string='Total Deposit (Reservation Payments)',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    refund_amount = fields.Monetary(
        string='Total Refund',
        compute='_compute_refund_amount',
        store=True,
        currency_field='currency_id',
        tracking=True,
    )
    refund_bank_line_ids = fields.One2many(
        'property.pre.contract.refund.bank.line',
        'refund_id',
        string='Bank Account Refund Lines',
        copy=True,
    )
    prior_refund_amount = fields.Monetary(
        string='Already Requested/Refunded',
        compute='_compute_amounts',
        currency_field='currency_id',
    )
    available_refund_amount = fields.Monetary(
        string='Available Refund Amount',
        compute='_compute_amounts',
        currency_field='currency_id',
    )
    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        compute='_compute_amounts',
        currency_field='currency_id',
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'pre_contract_refund_attachment_rel',
        'refund_id',
        'attachment_id',
        string='Attachments',
    )
    document_line_ids = fields.One2many(
        'property.pre.contract.refund.document.line',
        'refund_id',
        string='Required Documents',
        default=lambda self: self._default_document_line_commands(),
        copy=True,
    )
    note = fields.Text(string='Notes')
    property_release_action = fields.Selection(
        [
            ('available', 'Make Property Available'),
            ('lock', 'Lock Property'),
        ],
        string='Property Action',
        tracking=True,
    )
    show_property_release_action = fields.Boolean(
        compute='_compute_show_property_release_action',
    )
    interview_started_by_id = fields.Many2one(
        'res.users',
        string='Interview Started By',
        readonly=True,
        copy=False,
    )
    interview_started_date = fields.Datetime(
        string='Interview Started On',
        readonly=True,
        copy=False,
    )
    interview_completed_by_id = fields.Many2one(
        'res.users',
        string='Interview Completed By',
        readonly=True,
        copy=False,
    )
    interview_completed_date = fields.Datetime(
        string='Interview Completed On',
        readonly=True,
        copy=False,
    )
    interview_q1 = fields.Text(
        string='Q1: What is the primary reason for cancelling?',
        compute='_compute_interview_q1',
        inverse='_inverse_interview_q1',
        store=True,
        readonly=False,
    )
    interview_q2 = fields.Text(string='Found Another Property')
    interview_q3 = fields.Text(string='Financial Constraint Support')
    interview_q4 = fields.Text(string='Project Benefits Awareness')
    interview_q5 = fields.Text(string='Customer Still Insists on Refund')
    is_paid = fields.Boolean(
        string='Paid',
        default=False,
        tracking=True,
        copy=False,
    )
    paid_date = fields.Datetime(
        string='Paid On',
        readonly=True,
        copy=False,
    )
    expected_execution_label = fields.Char(
        string='Expected Finance Execution',
        compute='_compute_expected_execution',
        store=True,
        readonly=True,
    )
    expected_execution_date = fields.Datetime(
        string='Expected Execution Date/Time',
        compute='_compute_expected_execution',
        store=True,
        readonly=True,
    )
    payment_reference = fields.Char(
        string='Payment Reference',
        copy=False,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_interview', 'Pending Interview'),
            ('interview', 'Interview'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('retained', 'Retained'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    checked_by_id = fields.Many2one(
        'res.users',
        string='Checked By',
        readonly=True,
        copy=False,
    )
    checked_date = fields.Datetime(
        string='Checked On',
        readonly=True,
        copy=False,
    )
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string='Approved On',
        readonly=True,
        copy=False,
    )
    audit_status = fields.Selection(
        [
            ('waiting', 'Waiting Audit'),
            ('audited', 'Audited'),
        ],
        string='Audit Status',
        default='waiting',
        tracking=True,
        copy=False,
    )
    audited_by_id = fields.Many2one(
        'res.users',
        string='Audited By',
        readonly=True,
        copy=False,
    )
    audited_date = fields.Datetime(
        string='Audited On',
        readonly=True,
        copy=False,
    )
    audit_note = fields.Text(
        string='Audit Note',
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        copy=False,
        tracking=True,
    )
    credit_note_id = fields.Many2one(
        'account.move',
        string='Credit Note',
        readonly=True,
        copy=False,
    )
    payment_line_ids = fields.Many2many(
        'property.reservation.payment',
        compute='_compute_payment_lines',
        string='Verified Reservation Payments',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    eligible_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_eligible_domains',
    )
    eligible_reservation_ids = fields.Many2many(
        'property.reservation',
        compute='_compute_eligible_domains',
    )
    is_payment_viewer_only = fields.Boolean(
        compute='_compute_is_payment_viewer_only',
    )

    REFUNDABLE_RESERVATION_STATUSES = (
        'reserved',
        'expired',
        'pending_sales',
    )
    PROPERTY_ACTION_RESERVATION_STATUSES = (
        'reserved',
        'pending_sales',
        'sales_confirmed',
        'sold',
    )
    SUBMISSION_FIELDS = (
        'partner_id',
        'reservation_id',
        'refund_bank_line_ids',
        'attachment_ids',
        'document_line_ids',
        'refund_type_id',
        'payment_option',
        'note',
    )

    def _compute_is_payment_viewer_only(self):
        viewer_group = 'pre_contract_refund.group_pre_contract_refund_payment_viewer'
        other_groups = (
            'pre_contract_refund.group_pre_contract_refund_user',
            'pre_contract_refund.group_pre_contract_refund_manager',
            'pre_contract_refund.group_pre_contract_refund_deputy_head_pmca',
            'pre_contract_refund.group_pre_contract_refund_head_pmca',
        )
        is_viewer = self.env.user.has_group(viewer_group)
        has_other_refund_role = any(
            self.env.user.has_group(group_xmlid) for group_xmlid in other_groups
        )
        for rec in self:
            rec.is_payment_viewer_only = is_viewer and not has_other_refund_role

    @api.model
    def _default_document_line_commands(self):
        label_xmlids = {
            'application_letter': 'pre_contract_refund.document_label_application_letter',
            'crv': 'pre_contract_refund.document_label_crv',
            'deposit_slip_cpo': 'pre_contract_refund.document_label_deposit_slip_cpo',
            'id_copy': 'pre_contract_refund.document_label_id_copy',
        }
        def line(sequence, code):
            label = self.env.ref(label_xmlids[code], raise_if_not_found=False)
            vals = {'sequence': sequence, 'document_type': code}
            if label:
                vals['document_label_id'] = label.id
            return (0, 0, vals)
        return [
            line(10, 'application_letter'),
            line(20, 'crv'),
            line(30, 'deposit_slip_cpo'),
            line(40, 'id_copy'),
        ]

    @api.depends('reservation_id')
    def _compute_sales_supervisor_name(self):
        for rec in self:
            reservation = rec.reservation_id
            supervisor = (
                reservation.supervisor_id
                if reservation and 'supervisor_id' in reservation._fields
                else False
            )
            rec.sales_supervisor_name = supervisor.display_name if supervisor else False

    def _is_other_refund_reason(self):
        self.ensure_one()
        return (self.refund_reason_id.name or '').strip().lower() == 'other'

    @api.depends('refund_reason_id', 'refund_reason_id.name')
    def _compute_is_other_refund_reason(self):
        for rec in self:
            rec.is_other_refund_reason = rec._is_other_refund_reason() if rec.refund_reason_id else False

    @api.depends('refund_reason_id', 'refund_reason_id.name', 'refund_reason_other')
    def _compute_interview_q1(self):
        for rec in self:
            if rec.refund_reason_id and rec._is_other_refund_reason():
                rec.interview_q1 = rec.refund_reason_other or rec.refund_reason_id.name
            else:
                rec.interview_q1 = rec.refund_reason_id.name if rec.refund_reason_id else False

    def _inverse_interview_q1(self):
        other_reason = self.env.ref(
            'pre_contract_refund.refund_reason_other',
            raise_if_not_found=False,
        )
        for rec in self:
            answer = (rec.interview_q1 or '').strip()
            if not answer:
                rec.refund_reason_id = False
                rec.refund_reason_other = False
                continue
            reason = self.env['property.pre.contract.refund.reason'].search([
                ('name', '=ilike', answer),
            ], limit=1)
            if reason:
                rec.refund_reason_id = reason
                rec.refund_reason_other = False
            elif other_reason:
                rec.refund_reason_id = other_reason
                rec.refund_reason_other = answer

    @api.depends('refund_reason_id', 'refund_reason_id.name', 'refund_reason_other')
    def _compute_actual_refund_reason(self):
        for rec in self:
            if rec.refund_reason_id and rec._is_other_refund_reason():
                rec.actual_refund_reason = rec.refund_reason_other or rec.refund_reason_id.name
            else:
                rec.actual_refund_reason = rec.refund_reason_id.name if rec.refund_reason_id else False

    @api.depends('payment_option', 'approved_date')
    def _compute_expected_execution(self):
        for rec in self:
            rec.expected_execution_label = False
            rec.expected_execution_date = False
            if rec.payment_option == 'immediate':
                rec.expected_execution_label = _('4 hours')
                rec.expected_execution_date = (
                    rec.approved_date + timedelta(hours=4)
                    if rec.approved_date
                    else False
                )
            elif rec.payment_option == 'normal':
                rec.expected_execution_label = _('2 business days')
                rec.expected_execution_date = (
                    rec._add_business_days(rec.approved_date, 2)
                    if rec.approved_date
                    else False
                )

    def _add_business_days(self, start_datetime, business_days):
        current = start_datetime
        added = 0
        while added < business_days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current

    @api.model
    def _base_reservation_domain(self):
        # Quick reservations usually have no payment, so exclude them.
        # Pre-contract refunds are limited to active pre-sale reservations.
        return [
            ('partner_id', '!=', False),
            ('reservation_type_id.reservation_type', '!=', 'quick'),
            ('status', 'in', self.REFUNDABLE_RESERVATION_STATUSES),
            ('pre_contract_refunded', '=', False),
        ]

    def _validate_reservation_refundable(self):
        status_labels = dict(
            self.env['property.reservation']._fields['status']._description_selection(
                self.env
            )
        )
        for rec in self:
            if not rec.reservation_id:
                continue
            status = rec.reservation_id.status
            if status in rec.REFUNDABLE_RESERVATION_STATUSES:
                if not rec.reservation_id.pre_contract_refunded:
                    continue
            status_label = status_labels.get(status, status)
            raise ValidationError(_(
                'Cannot refund this reservation. Current status: %s. '
                'Only Reserved, Expired, and Pending Sales reservations that were not already refunded are allowed.'
            ) % status_label)

    @api.depends('reservation_id')
    def _compute_wing_name(self):
        for rec in self:
            reservation = rec.reservation_id
            wing = reservation.wing_id if reservation and 'wing_id' in reservation._fields else False
            rec.wing_name = wing.display_name if wing else ''

    @api.depends('refund_type_code', 'reservation_id.status')
    def _compute_show_property_release_action(self):
        for rec in self:
            rec.show_property_release_action = (
                rec.refund_type_code == 'full_cancellation'
                and rec.reservation_id.status in rec.PROPERTY_ACTION_RESERVATION_STATUSES
            )

    @api.model
    def _get_reservation_partner_ids(self):
        """Partners that have at least one reservation history record."""
        reservations = self.env['property.reservation'].search(self._base_reservation_domain())
        return reservations.mapped('partner_id').ids or [0]

    def _get_reservation_domain(self):
        domain = list(self._base_reservation_domain())
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    @api.depends('partner_id', 'reservation_id', 'reservation_id.pre_contract_refunded')
    def _compute_eligible_domains(self):
        reservations_obj = self.env['property.reservation']
        partner_ids = self._get_reservation_partner_ids()
        for rec in self:
            base_domain = self._base_reservation_domain()
            rec.eligible_partner_ids = [(6, 0, partner_ids)]
            if rec.partner_id:
                reservation_ids = reservations_obj.search(
                    base_domain + [('partner_id', '=', rec.partner_id.id)]
                ).ids
            else:
                reservation_ids = reservations_obj.search(base_domain).ids
            rec.eligible_reservation_ids = [(6, 0, reservation_ids)]

    @api.depends(
        'reservation_id',
        'reservation_id.payment_line_ids',
        'reservation_id.payment_line_ids.payment_status',
        'reservation_id.payment_line_ids.pre_contract_refunded',
    )
    def _compute_payment_lines(self):
        for rec in self:
            if rec.reservation_id:
                rec.payment_line_ids = rec.reservation_id.payment_line_ids.filtered(
                    lambda p: p.payment_status != 'canceled' and not p.pre_contract_refunded
                )
            else:
                rec.payment_line_ids = self.env['property.reservation.payment']

    @api.depends(
        'reservation_id',
        'reservation_id.property_id',
        'reservation_id.site_id',
        'payment_line_ids',
        'payment_line_ids.document_type_id',
    )
    def _compute_unit_and_payment_info(self):
        for rec in self:
            parts = []
            if rec.site_id:
                parts.append(rec.site_id.display_name)
            prop = rec.property_id
            if prop:
                if 'block' in prop._fields and prop.block:
                    parts.append(prop.block.display_name)
                if 'floor_id' in prop._fields and prop.floor_id:
                    parts.append('Floor %s' % prop.floor_id.display_name)
                parts.append(prop.display_name or prop.name or '')
            rec.unit_details = ' / '.join(filter(None, parts))

            methods = rec.payment_line_ids.mapped('document_type_id.name')
            rec.original_payment_method = ', '.join(dict.fromkeys(filter(None, methods)))

    @api.depends('payment_line_ids', 'payment_line_ids.document_type_id')
    def _compute_payment_flags(self):
        for rec in self:
            names = [
                name.lower()
                for name in rec.payment_line_ids.mapped('document_type_id.name')
                if name
            ]
            rec.crv_required = any('crv' in name for name in names)
            rec.is_cpo_crv_case = (
                any('cpo' in name for name in names)
                and any('crv' in name for name in names)
            )

    @api.depends('refund_bank_line_ids.amount')
    def _compute_refund_amount(self):
        for rec in self:
            rec.refund_amount = sum(rec.refund_bank_line_ids.mapped('amount'))

    def _get_prior_active_refund_amount(self, payment_lines=None):
        self.ensure_one()
        if not self.reservation_id:
            return 0.0
        if payment_lines:
            domain = [
                ('payment_line_id', 'in', payment_lines.ids),
                ('refund_id.state', 'not in', ('retained',)),
            ]
            if self.id:
                domain.append(('refund_id', '!=', self.id))
            lines = self.env['property.pre.contract.refund.bank.line'].search(domain)
            return sum(lines.mapped('amount'))
        domain = [
            ('reservation_id', '=', self.reservation_id.id),
            ('state', 'not in', ('retained',)),
        ]
        if self.id:
            domain.append(('id', '!=', self.id))
        refunds = self.search(domain)
        return sum(refunds.mapped('refund_amount'))

    def _get_available_refund_amount(self):
        self.ensure_one()
        if self.refund_type_code == 'overpayment':
            selected_payments = self.refund_bank_line_ids.mapped('payment_line_id')
            if not selected_payments:
                return 0.0
            total = sum(selected_payments.mapped('amount'))
            return max(total - self._get_prior_active_refund_amount(selected_payments), 0.0)
        total = self.total_deposit_amount or sum(self.payment_line_ids.mapped('amount'))
        return max(total - self._get_prior_active_refund_amount(), 0.0)

    @api.depends(
        'reservation_id',
        'refund_amount',
        'refund_type_code',
        'refund_bank_line_ids.payment_line_id',
        'refund_bank_line_ids.payment_line_id.amount',
    )
    def _compute_amounts(self):
        for rec in self:
            payments = rec.payment_line_ids
            total = sum(payments.mapped('amount'))
            if rec.refund_type_code == 'overpayment':
                selected_payments = rec.refund_bank_line_ids.mapped('payment_line_id')
                selected_total = sum(selected_payments.mapped('amount'))
                prior = (
                    rec._get_prior_active_refund_amount(selected_payments)
                    if selected_payments
                    else 0.0
                )
                available = max(selected_total - prior, 0.0)
            else:
                prior = rec._get_prior_active_refund_amount() if rec.reservation_id else 0.0
                available = max(total - prior, 0.0)
            rec.total_deposit_amount = total
            rec.prior_refund_amount = prior
            rec.available_refund_amount = available
            refund = rec.refund_amount or 0.0
            rec.remaining_amount = max(available - refund, 0.0)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.reservation_id = False
        self.refund_bank_line_ids = [(5, 0, 0)]

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        if self.reservation_id:
            self.partner_id = self.reservation_id.partner_id
            self.refund_type = self.refund_type_code or 'full_cancellation'
            if not self.refund_type_id:
                self.refund_type_id = self.env.ref(
                    'pre_contract_refund.refund_type_full_cancellation',
                    raise_if_not_found=False,
                )
            all_valid = self.reservation_id.payment_line_ids.filtered(
                lambda p: p.payment_status != 'canceled' and not p.pre_contract_refunded
            )
            total = sum(all_valid.mapped('amount'))
            prior = self._get_prior_active_refund_amount()
            available = max(total - prior, 0.0)
            self.refund_bank_line_ids = [(5, 0, 0)]
            if available:
                self.refund_bank_line_ids = [(0, 0, {
                    'amount': available,
                    'account_holder': self.partner_id.name if self.partner_id else False,
                })]
            self.cpo_crv_originals_received = False
            self.property_release_action = False
            if total and not available:
                return {
                    'warning': {
                        'title': _('No Remaining Refund Amount'),
                        'message': _(
                            'This reservation already has active refund request(s) '
                            'covering the full deposit.'
                        ),
                    }
                }

    @api.onchange('refund_type_id')
    def _onchange_refund_type_id(self):
        self.refund_type = self.refund_type_code or 'full_cancellation'
        if self.refund_type_code == 'overpayment':
            self.property_release_action = False

    @api.onchange(
        'partner_id',
        'reservation_id',
        'refund_bank_line_ids',
        'refund_type_id',
        'cpo_crv_originals_received',
        'note',
    )
    def _onchange_submission_fields(self):
        for rec in self:
            if rec.id and rec.state == 'draft':
                rec.is_submitted = False

    @api.constrains('reservation_id')
    def _check_reservation_refundable(self):
        self._validate_reservation_refundable()

    @api.constrains('partner_id', 'reservation_id')
    def _check_partner_has_reservation(self):
        for rec in self:
            if not rec.partner_id or not rec.reservation_id:
                continue
            if rec.reservation_id.partner_id != rec.partner_id:
                raise ValidationError(
                    _('The selected reservation does not belong to this customer.')
                )

    @api.constrains('reservation_id', 'refund_amount', 'state')
    def _check_refund_amount(self):
        for rec in self:
            if rec.refund_amount < 0:
                raise ValidationError(_('Refund amount cannot be negative.'))
            if rec.state in ('pending_interview', 'interview', 'pending_approval', 'approved', 'paid') and rec.refund_amount <= 0:
                raise ValidationError(_('Refund amount must be greater than zero.'))
            available = rec._get_available_refund_amount()
            if (
                rec.refund_type_code == 'overpayment'
                and not rec.refund_bank_line_ids.mapped('payment_line_id')
            ):
                continue
            if rec.reservation_id and available <= 0 and rec.state != 'retained':
                raise ValidationError(_(
                    'This reservation has no remaining refundable amount. '
                    'Active requests already cover the deposit.'
                ))
            if rec.refund_amount > available and available > 0:
                raise ValidationError(
                    _('Refund amount (%s) cannot exceed available refund amount (%s).')
                    % (rec.refund_amount, available)
                )

    @api.model
    def _next_refund_reference(self, refund_date=None):
        refund_date = fields.Date.to_date(refund_date) or fields.Date.context_today(self)
        prefix = 'REF-PRE-%s-' % refund_date.strftime('%Y%m%d')
        existing_refs = self.search([
            ('name', '=like', prefix + '%'),
        ]).mapped('name')
        last_number = 0
        for ref in existing_refs:
            suffix = (ref or '').replace(prefix, '', 1)
            if suffix.isdigit():
                last_number = max(last_number, int(suffix))
        return '%s%04d' % (prefix, last_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self._next_refund_reference(vals.get('date'))
            vals['is_submitted'] = False
            if 'document_line_ids' not in vals:
                vals['document_line_ids'] = self._default_document_line_commands()
        records = super().create(vals_list)
        records._link_attachments()
        records._link_document_attachments()
        for record in records.filtered(lambda r: r.state == 'draft'):
            record._validate_submission()
            record._log_event(
                _('Refund request created'),
                record._format_refund_amount_log_details(),
            )
        return records

    def write(self, vals):
        if self.env.context.get('skip_submission_update'):
            return super().write(vals)
        changed_fields = set(vals)
        submission_changed = any(field in changed_fields for field in self.SUBMISSION_FIELDS)
        if submission_changed and 'state' not in vals:
            vals = dict(vals)
            vals['is_submitted'] = False
        if 'state' not in vals:
            for rec in self:
                if rec.state != 'draft' and any(
                    f in vals
                    for f in self.SUBMISSION_FIELDS + (
                        'refund_amount',
                        'date',
                        'payment_option',
                        'crv_front_attachment_id',
                        'crv_back_attachment_id',
                        'application_letter_attachment_id',
                        'deposit_slip_attachment_id',
                        'id_copy_attachment_id',
                    )
                ):
                    raise UserError(_('Only draft records can be edited. Reset to draft first.'))
        res = super().write(vals)
        if any(
            field in vals
            for field in (
                'attachment_ids',
                'crv_front_attachment_id',
                'crv_back_attachment_id',
                'application_letter_attachment_id',
                'deposit_slip_attachment_id',
                'id_copy_attachment_id',
            )
        ):
            self._link_attachments()
            self._link_document_attachments()
        for record in self.filtered(lambda r: r.state == 'draft'):
            record._validate_submission()
        if submission_changed:
            for record in self.filtered(lambda r: r.state == 'draft'):
                record._log_event(
                    _('Refund request updated'),
                    record._format_update_log_details(changed_fields),
                )
        return res

    def unlink(self):
        raise UserError(_('Refund records cannot be deleted.'))

    def _link_attachments(self):
        """Bind uploaded attachments to this record so users can read them."""
        for rec in self:
            for attachment in rec.attachment_ids:
                if attachment.res_model != rec._name or attachment.res_id != rec.id:
                    attachment.sudo().write({
                        'res_model': rec._name,
                        'res_id': rec.id,
                    })

    def _link_document_attachments(self):
        attachment_fields = (
            'crv_front_attachment_id',
            'crv_back_attachment_id',
            'application_letter_attachment_id',
            'deposit_slip_attachment_id',
            'id_copy_attachment_id',
        )
        for rec in self:
            for field_name in attachment_fields:
                attachment = rec[field_name]
                if attachment and (
                    attachment.res_model != rec._name or attachment.res_id != rec.id
                ):
                    attachment.sudo().write({
                        'res_model': rec._name,
                        'res_id': rec.id,
                    })

    def _validate_submission(self):
        self.ensure_one()
        self._validate_reservation_refundable()
        if self.total_deposit_amount <= 0:
            raise ValidationError(_('Deposit amount must be greater than zero.'))
        if not self.refund_type_id:
            raise ValidationError(_('Please select a refund type.'))
        if self.refund_type_code not in ('full_cancellation', 'overpayment'):
            raise ValidationError(_('Refund type must be Full Cancellation or Overpayment.'))
        if not self.payment_option:
            raise ValidationError(_('Please select a payment option.'))
        if not self.refund_bank_line_ids:
            raise UserError(_('Please add customer bank account details.'))
        invalid_lines = self.refund_bank_line_ids.filtered(
            lambda line: (
                not line.bank_id
                or not line.account_detail_id
                or not (line.account_holder or '').strip()
                or line.amount <= 0
            )
        )
        if invalid_lines:
            raise UserError(_(
                'Each bank line must have bank name, account number, account holder, '
                'and an amount greater than zero.'
            ))
        if self.refund_type_code == 'overpayment' and any(
            not line.payment_line_id for line in self.refund_bank_line_ids
        ):
            raise UserError(_('Please select the reservation payment to deduct from for overpayment refunds.'))
        for payment in self.refund_bank_line_ids.mapped('payment_line_id'):
            if payment.reservation_id != self.reservation_id:
                raise ValidationError(_('Selected reservation payments must belong to this reservation.'))
            if payment.pre_contract_refunded:
                raise ValidationError(_('Selected reservation payments must not already be refunded.'))
            if payment.ref_number:
                duplicated = self.env['property.reservation.payment'].search([
                    ('id', '!=', payment.id),
                    ('reservation_id', '=', self.reservation_id.id),
                    ('ref_number', '=', payment.ref_number),
                    ('pre_contract_refunded', '=', True),
                ], limit=1)
                if duplicated:
                    raise ValidationError(_(
                        'Payment reference %s was already refunded and cannot be selected again.'
                    ) % payment.ref_number)
            line_total = sum(
                self.refund_bank_line_ids.filtered(
                    lambda line, payment=payment: line.payment_line_id == payment
                ).mapped('amount')
            )
            if line_total > payment.amount:
                raise ValidationError(_(
                    'Refund amount for payment reference %s cannot exceed its payment amount.'
                ) % (payment.ref_number or payment.display_name))
        available = self._get_available_refund_amount()
        if available <= 0:
            raise ValidationError(_(
                'This reservation is already fully requested/refunded.'
            ))
        if self.refund_amount > available:
            raise ValidationError(_(
                'Only %s remains available to refund for this reservation.'
            ) % available)
        if (
            self.refund_type_code == 'full_cancellation'
            and float_compare(
                self.refund_amount,
                available,
                precision_rounding=self.currency_id.rounding,
            ) != 0
        ):
            raise ValidationError(_(
                'Full cancellation refunds must refund the full available reservation amount (%s).'
            ) % available)
        document_lines = self.document_line_ids.filtered(lambda line: line.file)
        uploaded_types = set(document_lines.mapped('document_type'))
        missing_documents = []
        if (
            'application_letter' not in uploaded_types
            and not self.application_letter_attachment_id
        ):
            missing_documents.append(_('Application Letter'))
        if (
            self.crv_required
            and 'crv' not in uploaded_types
            and not self.crv_front_attachment_id
        ):
            missing_documents.append(_('CRV'))
        if (
            'deposit_slip_cpo' not in uploaded_types
            and not self.deposit_slip_attachment_id
        ):
            missing_documents.append(_('Deposit Slip / CPO'))
        if 'id_copy' not in uploaded_types and not self.id_copy_attachment_id:
            missing_documents.append(_('ID Copy'))
        if missing_documents:
            raise ValidationError(_(
                'Please upload the mandatory labelled documents: %s.'
            ) % ', '.join(missing_documents))
        if not document_lines and not self.attachment_ids and not any((
            self.application_letter_attachment_id,
            self.crv_front_attachment_id,
            self.crv_back_attachment_id,
            self.deposit_slip_attachment_id,
            self.id_copy_attachment_id,
        )):
            raise ValidationError(_(
                'Please upload the required refund document in the Attachments tab.'
            ))

    def _format_update_log_details(self, changed_fields):
        self.ensure_one()
        field_labels = {
            'partner_id': _('Customer'),
            'reservation_id': _('Reservation'),
            'refund_bank_line_ids': _('Bank Account Refund'),
            'attachment_ids': _('Attachments'),
            'refund_type_id': _('Refund Type'),
            'payment_option': _('Payment Option'),
            'note': _('Notes'),
        }
        labels = [
            field_labels[field_name]
            for field_name in self.SUBMISSION_FIELDS
            if field_name in changed_fields
        ]
        details = self._format_refund_amount_log_details()
        if labels:
            details = '%s. %s' % (_('Updated: %s') % ', '.join(labels), details)
        return details

    def _format_refund_amount_log_details(self):
        self.ensure_one()
        return _('Refund Amount: %s %s') % (
            self.refund_amount,
            self.currency_id.name or '',
        )

    def _log_event(self, title, details=None):
        self.ensure_one()
        body = Markup('<b>%s</b>') % title
        if details:
            body += Markup('<br/>%s') % details
        self.message_post(body=body)

    def action_save_draft(self):
        """Explicit save in draft — keeps record editable for users."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be saved as draft.'))
            rec._validate_submission()
            rec._link_attachments()
            rec._link_document_attachments()
            rec._log_event(_('Draft saved'))

    def action_submit(self):
        """Validate mandatory refund data and send it to the correct PMCA queue."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            rec._validate_submission()
            rec._link_attachments()
            rec._link_document_attachments()
            rec._clear_pmca_activities()
            next_state = (
                'pending_interview'
                if rec.refund_type_code == 'full_cancellation'
                else 'pending_approval'
            )
            rec.with_context(skip_submission_update=True).write({
                'is_submitted': True,
                'state': next_state,
            })
            rec._schedule_pmca_activity()
            rec._log_event(
                _('Refund request submitted'),
                _('Refund Amount: %s %s') % (
                    rec.refund_amount,
                    rec.currency_id.name or '',
                ),
            )

    def _clear_pmca_activities(self):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        if activities:
            activities.unlink()

    def _is_deputy_amount(self):
        self.ensure_one()
        return self.refund_amount <= 500000

    def _can_handle_amount_queue(self):
        self.ensure_one()
        if self.env.user.has_group('pre_contract_refund.group_pre_contract_refund_manager'):
            return True
        group_xmlid = (
            'pre_contract_refund.group_pre_contract_refund_deputy_head_pmca'
            if self._is_deputy_amount()
            else 'pre_contract_refund.group_pre_contract_refund_head_pmca'
        )
        return self.env.user.has_group(group_xmlid)

    def _ensure_amount_queue_user(self):
        self.ensure_one()
        if not self._can_handle_amount_queue():
            role = _('Deputy Head of PMCA') if self._is_deputy_amount() else _('Head of PMCA')
            raise UserError(_('Only %s can process this refund amount.') % role)

    def _ensure_head_pmca_user(self):
        if not self.env.user.has_group('pre_contract_refund.group_pre_contract_refund_head_pmca'):
            raise UserError(_('Only Head of PMCA can make the final approval decision.'))

    def _ensure_auditor_user(self):
        if not (
            self.env.user.has_group('pre_contract_refund.group_pre_contract_refund_auditor')
            or self.env.user.has_group('pre_contract_refund.group_pre_contract_refund_manager')
        ):
            raise UserError(_('Only a Pre Contract Refund Auditor can audit this refund.'))

    def _schedule_pmca_activity(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        deputy_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_deputy_head_pmca',
            raise_if_not_found=False,
        )
        head_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_head_pmca',
            raise_if_not_found=False,
        )
        for rec in self:
            group = (
                deputy_group
                if rec.state == 'pending_interview' and rec._is_deputy_amount()
                else head_group
            )
            users = group.users if group else self.env['res.users']
            summary = (
                _('Conduct retention interview for refund request %s') % rec.name
                if rec.state == 'pending_interview'
                else _('Approve refund request %s') % rec.name
            )
            for user in users:
                rec.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=summary,
                )

    def _schedule_audit_activity(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        auditor_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_auditor',
            raise_if_not_found=False,
        )
        if not activity_type or not auditor_group:
            return
        for rec in self.filtered(lambda refund: refund.state == 'approved' and refund.audit_status == 'waiting'):
            for user in auditor_group.users:
                rec.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=_('Audit refund request %s before finance execution') % rec.name,
                )

    def action_start_interview(self):
        for rec in self:
            if rec.state != 'pending_interview':
                raise UserError(_('Only pending interview requests can be started.'))
            rec._ensure_amount_queue_user()
            rec.write({
                'state': 'interview',
                'interview_started_by_id': self.env.user.id,
                'interview_started_date': fields.Datetime.now(),
            })
            rec._clear_pmca_activities()
            rec._log_event(_('Retention interview started'))

    def _validate_interview_answers(self):
        self.ensure_one()
        missing = []
        if not self.refund_reason_id:
            missing.append(_('Primary reason for cancelling'))
        elif self._is_other_refund_reason() and not (self.refund_reason_other or '').strip():
            missing.append(_('Other refund reason details'))
        missing += [
            label for field_name, label in (
                ('interview_q2', _('Found another property')),
                ('interview_q3', _('Financial constraint support')),
                ('interview_q4', _('Project benefits awareness')),
                ('interview_q5', _('Customer still insists on refund')),
            )
            if not (self[field_name] or '').strip()
        ]
        if missing:
            raise ValidationError(_('Please complete all interview answers: %s') % ', '.join(missing))

    def action_retain(self):
        for rec in self:
            if rec.state not in ('interview', 'pending_approval'):
                raise UserError(_('Only interview or approval requests can be retained.'))
            if rec.refund_type_code != 'full_cancellation':
                raise UserError(_('Retention is only available for full cancellation refunds.'))
            if rec.state == 'pending_approval':
                rec._ensure_head_pmca_user()
            else:
                rec._ensure_amount_queue_user()
            if rec.refund_type_code == 'full_cancellation' and rec.state == 'interview':
                rec._validate_interview_answers()
            rec.write({
                'state': 'retained',
                'interview_completed_by_id': self.env.user.id,
                'interview_completed_date': fields.Datetime.now(),
            })
            rec._clear_pmca_activities()
            rec._log_event(_('Customer retained'))

    def action_proceed_to_refund(self):
        for rec in self:
            if rec.state != 'interview':
                raise UserError(_('Only started interviews can proceed to approval.'))
            rec._ensure_amount_queue_user()
            rec._validate_interview_answers()
            rec.write({
                'state': 'pending_approval',
                'interview_completed_by_id': self.env.user.id,
                'interview_completed_date': fields.Datetime.now(),
            })
            rec._clear_pmca_activities()
            rec._schedule_pmca_activity()
            rec._log_event(_('Retention interview completed'))

    def action_approve(self):
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only requests pending approval can be approved.'))
            rec._ensure_head_pmca_user()
            if rec.show_property_release_action and not rec.property_release_action:
                raise ValidationError(_('Please choose whether to make the property available or lock it.'))
            rec._apply_property_release_action()
            if not rec.credit_note_id:
                rec._create_credit_note_draft()
            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'audit_status': 'waiting',
                'audited_by_id': False,
                'audited_date': False,
            })
            rec._clear_pmca_activities()
            rec._schedule_audit_activity()
            rec._log_event(
                _('Approved'),
                _('Credit note %s created in draft.') % rec.credit_note_id.display_name,
            )

    def action_audit_refund(self):
        for rec in self:
            if rec.state != 'approved' or rec.is_paid:
                raise UserError(_('Only approved refunds waiting for finance can be audited.'))
            if rec.audit_status == 'audited':
                raise UserError(_('This refund has already been audited.'))
            rec._ensure_auditor_user()
            rec.write({
                'audit_status': 'audited',
                'audited_by_id': self.env.user.id,
                'audited_date': fields.Datetime.now(),
            })
            details = _('Audited by %s.') % self.env.user.display_name
            if rec.audit_note:
                details = '%s<br/>%s' % (details, rec.audit_note)
            rec._clear_pmca_activities()
            rec._log_event(_('Refund audited'), details)

    def _apply_property_release_action(self):
        self.ensure_one()
        if not self.show_property_release_action:
            return
        if self.property_release_action == 'available':
            self.property_id.sudo().write({'state': 'available'})
            self.reservation_id.sudo().write({'status': 'canceled'})
        elif self.property_release_action == 'lock':
            vals = {
                'state': 'lock',
                'is_locked': True,
                'locked_by_id': self.env.user.id,
                'locked_date': fields.Datetime.now(),
            }
            if (
                'state_before_lock' in self.property_id._fields
                and self.property_id.state in ('draft', 'available')
            ):
                vals['state_before_lock'] = self.property_id.state
            self.property_id.sudo().write(vals)
            self.reservation_id.sudo().write({'status': 'canceled'})

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'draft':
                raise UserError(_('This request cannot be reset to draft.'))
            if rec.state not in ('pending_interview', 'interview'):
                raise UserError(_('Only requests before final approval review can be reset to draft.'))
            if not self.env.user.has_group('pre_contract_refund.group_pre_contract_refund_manager'):
                rec._ensure_amount_queue_user()
            rec.write({
                'state': 'draft',
                'checked_by_id': False,
                'checked_date': False,
                'rejection_reason': False,
                'approved_by_id': False,
                'approved_date': False,
                'audit_status': 'waiting',
                'audited_by_id': False,
                'audited_date': False,
                'audit_note': False,
                'interview_started_by_id': False,
                'interview_started_date': False,
                'interview_completed_by_id': False,
                'interview_completed_date': False,
                'is_paid': False,
                'paid_date': False,
                'is_submitted': False,
            })
            rec._clear_pmca_activities()
            rec._log_event(_('Reset to draft'))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_register_payment(self):
        raise UserError(_('Register payment from the linked credit note.'))

    def _mark_paid_from_credit_note(self):
        for rec in self:
            if rec.state != 'approved' or rec.is_paid:
                continue
            payment_reference = rec.credit_note_id.name or rec.credit_note_id.ref or rec.payment_reference
            rec.sudo().write({
                'state': 'paid',
                'is_paid': True,
                'paid_date': fields.Datetime.now(),
                'payment_reference': payment_reference,
            })
            rec._mark_reservation_payments_refunded()
            rec._clear_pmca_activities()
            rec._log_event(_('Refund paid'), _('Paid from credit note payment.'))

    def _mark_reservation_payments_refunded(self):
        for rec in self:
            if rec.refund_type_code == 'full_cancellation':
                rec.reservation_id.sudo().write({'pre_contract_refunded': True})
                payment_lines = rec.reservation_id.payment_line_ids.filtered(
                    lambda line: line.payment_status != 'canceled'
                )
            else:
                rec._apply_overpayment_to_reservation_payments()
                continue
            if payment_lines:
                payment_lines.sudo().write({
                    'pre_contract_refunded': True,
                    'pre_contract_refund_id': rec.id,
                })

    def _apply_overpayment_to_reservation_payments(self):
        self.ensure_one()
        deductions_by_payment = {}
        for line in self.refund_bank_line_ids.filtered('payment_line_id'):
            payment = line.payment_line_id
            if payment.id not in deductions_by_payment:
                deductions_by_payment[payment.id] = {
                    'payment': payment,
                    'amount': 0.0,
                }
            deductions_by_payment[payment.id]['amount'] += line.amount

        rounding = self.currency_id.rounding
        for values in deductions_by_payment.values():
            payment = values['payment']
            deduction = values['amount']
            current_amount = payment.amount or 0.0
            if float_compare(deduction, current_amount, precision_rounding=rounding) > 0:
                raise ValidationError(_(
                    'Overpayment refund amount (%s) cannot exceed current reservation payment amount (%s) for %s.'
                ) % (deduction, current_amount, payment.ref_number or payment.display_name))
            remaining_amount = max(current_amount - deduction, 0.0)
            payment.sudo().write({
                'amount': remaining_amount,
                'pre_contract_refunded': float_compare(
                    remaining_amount,
                    0.0,
                    precision_rounding=rounding,
                ) == 0,
                'pre_contract_refund_id': self.id,
            })
            self._log_event(
                _('Reservation payment updated'),
                _(
                    'Payment %s amount reduced from %s to %s because overpayment refund %s was paid.'
                ) % (
                    payment.ref_number or payment.display_name,
                    current_amount,
                    remaining_amount,
                    self.name,
                ),
            )
            payment.reservation_id.message_post(
                body=Markup(
                    '<b>%s</b><br/>%s'
                ) % (
                    _('Reservation payment adjusted'),
                    _(
                        'Payment %s amount changed from %s to %s. '
                        'Deducted %s because overpayment refund %s was paid.'
                    ) % (
                        payment.ref_number or payment.display_name,
                        current_amount,
                        remaining_amount,
                        deduction,
                        self.name,
                    ),
                )
            )

    def action_view_credit_note(self):
        self.ensure_one()
        if not self.credit_note_id:
            raise UserError(_('No credit note linked.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Note'),
            'res_model': 'account.move',
            'res_id': self.credit_note_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_credit_note_partner(self):
        self.ensure_one()
        account_holder = next(
            (
                (line.account_holder or '').strip()
                for line in self.refund_bank_line_ids
                if (line.account_holder or '').strip()
            ),
            '',
        )
        if not account_holder:
            return self.partner_id
        if self.partner_id.name == account_holder:
            return self.partner_id

        partner = self.env['res.partner'].search([
            ('name', '=ilike', account_holder),
        ], limit=1)
        if partner:
            return partner
        return self.env['res.partner'].create({
            'name': account_holder,
            'customer_rank': 1,
        })

    def _create_credit_note_draft(self):
        self.ensure_one()
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_('No sales journal found for this company.'))

        account_id = self.partner_id.property_account_receivable_id.id
        product = self.env.ref(
            'pre_contract_refund.product_pre_contract_refund',
            raise_if_not_found=False,
        )
        if product and product.property_account_income_id:
            account_id = product.property_account_income_id.id
        elif product and product.categ_id.property_account_income_categ_id:
            account_id = product.categ_id.property_account_income_categ_id.id
        if not account_id:
            account_id = self.env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('company_id', '=', self.company_id.id),
            ], limit=1).id
        if not account_id:
            raise UserError(_('No receivable account configured for refunds.'))

        bank_parts = [
            '%s / %s (%s)' % (line.bank_name, line.account_number, line.amount)
            for line in self.refund_bank_line_ids
            if line.bank_name and line.account_number
        ]
        line_name = _('Pre-contract refund: %s') % (self.reservation_id.display_name or self.name)
        if bank_parts:
            line_name += ' — %s' % ', '.join(bank_parts)

        credit_note_partner = self._get_credit_note_partner()
        move_vals = {
            'move_type': 'out_refund',
            'partner_id': credit_note_partner.id,
            'currency_id': self.currency_id.id,
            'invoice_date': self.date,
            'journal_id': journal.id,
            'ref': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': line_name,
                'quantity': 1,
                'price_unit': self.refund_amount,
                'account_id': account_id,
                'product_id': product.id if product else False,
                'tax_ids': [(5, 0, 0)],
            })],
        }
        move = self.env['account.move'].create(move_vals)
        move._compute_amount()
        self.credit_note_id = move.id
