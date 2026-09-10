# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TemerLead(models.Model):
    _inherit = 'temer.lead'

    from_special_sales = fields.Boolean("From Special Sales", default=False)

    lead_type_id = fields.Many2one(
        'temer.lead.type',
        string='Type',
        ondelete='restrict',
        tracking=True,
        help="Company/Freelance: select or create from dedicated models. Employee: select from Contacts.",
        default=lambda self: self.env['temer.lead.type'].search([('code', '=', 'company')], limit=1),
    )
    lead_type_code = fields.Char(related='lead_type_id.code', string='Type Code', readonly=True)

    # Type-specific: Many2one + Char backing; company_display/freelance_display = single UI field
    company_id = fields.Many2one(
        'crm.special.sales.company',
        string='Company',
        ondelete='set null',
    )
    company_name = fields.Char(help="New company name when not found; created on save.")
    company_display = fields.Char(
        string='Company',
        compute='_compute_company_display',
        inverse='_inverse_company_display',
        help="Search existing or type new; new ones are created on save.",
    )
    freelance_id = fields.Many2one(
        'crm.special.sales.freelance',
        string='Freelance',
        ondelete='set null',
    )
    freelance_name = fields.Char(help="New freelance name when not found; created on save.")
    freelance_display = fields.Char(
        string='Freelance',
        compute='_compute_freelance_display',
        inverse='_inverse_freelance_display',
        help="Search existing or type new; new ones are created on save.",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee (legacy)',
        ondelete='set null',
    )
    employee_ref_id = fields.Many2one(
        'crm.employee.ref',
        string='Employee',
        ondelete='set null',
    )

    # Legacy: keep for migration
    lead_type = fields.Selection([
        ('company', 'Company'),
        ('freelance', 'Freelance'),
        ('employee', 'Employee'),
    ], string='Type (legacy)', help="Deprecated: use Type above.")

    def _get_lead_type_code(self, vals=None):
        if vals is not None and 'lead_type_id' in vals:
            if vals['lead_type_id']:
                rec = self.env['temer.lead.type'].browse(vals['lead_type_id'])
                return rec.code if rec.exists() else None
            return None
        if self.lead_type_id:
            return self.lead_type_id.code
        return getattr(self, 'lead_type', None)

    @api.constrains('lead_type_id', 'employee_ref_id', 'company_id', 'company_name', 'freelance_id', 'freelance_name')
    def _check_special_sales_customer(self):
        for rec in self:
            if not rec.from_special_sales:
                continue
            code = rec._get_lead_type_code()
            if not code:
                continue
            if code == 'employee':
                if not rec.employee_ref_id:
                    raise ValidationError(_('For type Employee, you must select an Employee.'))
            elif code == 'company':
                if not rec.company_id and not (rec.company_name or '').strip():
                    raise ValidationError(_('For type Company, you must enter a Company name.'))
            elif code == 'freelance':
                if not rec.freelance_id and not (rec.freelance_name or '').strip():
                    raise ValidationError(_('For type Freelance, you must enter a Freelance name.'))

    @api.depends('company_id', 'company_name')
    def _compute_company_display(self):
        for rec in self:
            rec.company_display = (rec.company_id and rec.company_id.name) or (rec.company_name or '')

    def _inverse_company_display(self):
        for rec in self:
            val = (rec.company_display or '').strip()
            if not val:
                rec.company_id = False
                rec.company_name = False
            else:
                company = self.env['crm.special.sales.company'].search([('name', '=ilike', val)], limit=1)
                if company:
                    rec.company_id = company
                    rec.company_name = False
                else:
                    rec.company_id = False
                    rec.company_name = val

    @api.depends('freelance_id', 'freelance_name')
    def _compute_freelance_display(self):
        for rec in self:
            rec.freelance_display = (rec.freelance_id and rec.freelance_id.name) or (rec.freelance_name or '')

    def _inverse_freelance_display(self):
        for rec in self:
            val = (rec.freelance_display or '').strip()
            if not val:
                rec.freelance_id = False
                rec.freelance_name = False
            else:
                freelance = self.env['crm.special.sales.freelance'].search([('name', '=ilike', val)], limit=1)
                if freelance:
                    rec.freelance_id = freelance
                    rec.freelance_name = False
                else:
                    rec.freelance_id = False
                    rec.freelance_name = val

    def _get_or_create_company(self, name):
        name = (name or '').strip()
        if not name:
            return False
        company = self.env['crm.special.sales.company'].search([('name', '=ilike', name)], limit=1)
        if not company:
            company = self.env['crm.special.sales.company'].create({'name': name})
        return company.id

    def _get_or_create_freelance(self, name):
        name = (name or '').strip()
        if not name:
            return False
        freelance = self.env['crm.special.sales.freelance'].search([('name', '=ilike', name)], limit=1)
        if not freelance:
            freelance = self.env['crm.special.sales.freelance'].create({'name': name})
        return freelance.id

    @api.onchange('lead_type_id')
    def _onchange_lead_type_clear_others(self):
        """When Type changes: clear Company/Freelance/Employee so only one is set."""
        if not self.from_special_sales:
            return
        code = self._get_lead_type_code()
        if code == 'company':
            self.employee_ref_id = False
            self.freelance_id = False
            self.freelance_name = False
            self.freelance_display = False
        elif code == 'freelance':
            self.employee_ref_id = False
            self.company_id = False
            self.company_name = False
            self.company_display = False
        elif code == 'employee':
            self.company_id = False
            self.company_name = False
            self.company_display = False
            self.freelance_id = False
            self.freelance_name = False
            self.freelance_display = False

    def _clear_other_type_fields(self, code, vals):
        """When type changes, clear the other type's fields. One lead = one type."""
        if code == 'company':
            vals['employee_ref_id'] = False
            vals['freelance_id'] = False
            vals['freelance_name'] = False
        elif code == 'freelance':
            vals['employee_ref_id'] = False
            vals['company_id'] = False
            vals['company_name'] = False
        elif code == 'employee':
            vals['company_id'] = False
            vals['company_name'] = False
            vals['freelance_id'] = False
            vals['freelance_name'] = False

    @api.model
    def create(self, vals):
        vals = dict(vals)
        if vals.get('from_special_sales'):
            code = None
            if vals.get('lead_type_id'):
                lt = self.env['temer.lead.type'].browse(vals['lead_type_id'])
                code = lt.code if lt.exists() else None
            if code:
                self._clear_other_type_fields(code, vals)
            if code == 'company' and not vals.get('company_id') and (vals.get('company_name') or '').strip():
                vals['company_id'] = self._get_or_create_company(vals['company_name'])
            elif code == 'freelance' and not vals.get('freelance_id') and (vals.get('freelance_name') or '').strip():
                vals['freelance_id'] = self._get_or_create_freelance(vals['freelance_name'])
        return super().create(vals)

    def write(self, vals):
        vals = dict(vals) if vals else {}
        if len(self) == 1 and self.from_special_sales:
            code = self._get_lead_type_code(vals) or self._get_lead_type_code()
            if code:
                self._clear_other_type_fields(code, vals)
            if code == 'company' and not vals.get('company_id') and not self.company_id:
                name = (vals.get('company_name') or self.company_name or '').strip()
                if name:
                    vals['company_id'] = self._get_or_create_company(name)
            elif code == 'freelance' and not vals.get('freelance_id') and not self.freelance_id:
                name = (vals.get('freelance_name') or self.freelance_name or '').strip()
                if name:
                    vals['freelance_id'] = self._get_or_create_freelance(name)
        return super().write(vals)

    def _get_reservation_customer_partner_id(self):
        """Reservation Customer: use partner_id if set; else get/create partner from customer_name so it always shows."""
        self.ensure_one()
        if self.partner_id:
            return self.partner_id.id
        name = (self.customer_name or '').strip()
        if not name:
            return False
        partner = self.env['res.partner'].search([('name', '=ilike', name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'company_type': 'person',
            })
        return partner.id

    def action_reserve(self):
        """Always pass reservation Customer from lead: partner_id or customer_name (get/create), so Customer always appears."""
        for rec in self:
            partner_id = rec._get_reservation_customer_partner_id()
            action = super(TemerLead, rec).action_reserve()
            if action and action.get('context') and partner_id:
                ctx = dict(action['context'])
                ctx['default_partner_id'] = partner_id
                action['context'] = ctx
            return action
