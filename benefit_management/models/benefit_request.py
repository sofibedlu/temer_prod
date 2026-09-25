# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class BenefitRequest(models.Model):
    _name = 'benefit.request'
    _description = 'Benefit Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Request No', 
        required=True, 
        readonly=True, 
        copy=False, 
        default=lambda self: _('New')
    )
    
    # Filter only employees that have at least one active definition
    employee_id = fields.Many2one(
        'hr.employee', 
        string='Employee', 
        required=True, 
        tracking=True,
        domain="[('id', 'in', eligible_employee_ids)]"
    )
    eligible_employee_ids = fields.Many2many(
        'hr.employee', 
        compute='_compute_eligible_employees'
    )
    
    benefit_definition_id = fields.Many2one(
        'benefit.definition', 
        string='Benefit Definition', 
        required=True, 
        tracking=True,
        domain="[('employee_id', '=', employee_id)]"
    )
    benefit_type_id = fields.Many2one(
        related='benefit_definition_id.benefit_type_id', 
        string='Benefit Type', 
        store=True, 
        readonly=True
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', 
        string='Department', 
        store=True, 
        readonly=True
    )
    currency_id = fields.Many2one(
        related='benefit_definition_id.currency_id', 
        string='Currency', 
        readonly=True
    )
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    
    note = fields.Text(string='Note')
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'benefit_request_ir_attachments_rel', 
        'request_id', 
        'attachment_id', 
        string='Attachments'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    payment_request_id = fields.Many2one(
        'payment.request', 
        string='Payment Request', 
        readonly=True, 
        copy=False
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company, 
        required=True
    )

    @api.depends('company_id')
    def _compute_eligible_employees(self):
        definitions = self.env['benefit.definition'].search([('active', '=', True)])
        emp_ids = definitions.mapped('employee_id').ids
        for rec in self:
            rec.eligible_employee_ids = [(6, 0, emp_ids)]

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            definitions = self.env['benefit.definition'].search([('employee_id', '=', self.employee_id.id)])
            if len(definitions) == 1:
                self.benefit_definition_id = definitions[0].id
                self.amount = definitions[0].amount
            else:
                self.benefit_definition_id = False
                self.amount = 0.0
        else:
            self.benefit_definition_id = False
            self.amount = 0.0

    @api.onchange('benefit_definition_id')
    def _onchange_benefit_definition_id(self):
        if self.benefit_definition_id:
            self.amount = self.benefit_definition_id.amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('benefit.request') or _('New')
        records = super().create(vals_list)
        # Link attachments properly to document
        for rec in records:
            if rec.attachment_ids:
                rec.attachment_ids.sudo().write({
                    'res_model': self._name,
                    'res_id': rec.id,
                })
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            for rec in self:
                rec.attachment_ids.sudo().write({
                    'res_model': self._name,
                    'res_id': rec.id,
                })
        return res

    def action_check(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft requests can be checked."))
            rec.state = 'checked'
            rec.message_post(body=Markup(_("<b>Request Checked</b> by %s") % self.env.user.name))

    def action_approve(self):
        PaymentRequest = self.env['payment.request']
        for rec in self:
            if rec.state != 'checked':
                raise UserError(_("Only checked requests can be approved."))
            
            # Resolve Payee Partner from Employee
            emp = rec.employee_id
            partner = emp.work_contact_id or emp.user_id.partner_id
            if not partner:
                raise UserError(_(
                    "Employee '%s' does not have a linked Private or Work Contact (Partner). "
                    "Please assign a contact on the employee form to process payments."
                ) % emp.name)
            
            # Ensure partner satisfies domain requirement of payment.request
            if partner.supplier_rank == 0 and partner.customer_rank == 0:
                partner.sudo().write({'supplier_rank': 1})
            
            # Resolve currency
            currency = rec.currency_id or self.env.ref('base.ETB', raise_if_not_found=False) or rec.company_id.currency_id

            pr_vals = {
                'pay_to': 'employee',
                'partner_id': partner.id,
                'reason': f"Employee Benefit Payment: {emp.name} - {rec.benefit_type_id.name}. Note: {rec.note or 'N/A'}",
                'amount': rec.amount,
                'currency_id': currency.id,
                'company_id': rec.company_id.id,
                'state': 'draft',
            }
            payment_req = PaymentRequest.sudo().create(pr_vals)

            # Update definition last recurring date
            if rec.benefit_definition_id:
                rec.benefit_definition_id.sudo().write({
                    'last_recurring_date': fields.Date.context_today(self)
                })

            rec.write({
                'state': 'approved',
                'payment_request_id': payment_req.id,
            })

            rec.message_post(body=Markup(
                _("<b>Request Approved.</b><br/>Generated Payment Request: <b>%s</b>") % payment_req.pr_number
            ))

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body=Markup(_("<b>Request Rejected</b> by %s") % self.env.user.name))

    def action_view_payment_request(self):
        self.ensure_one()
        return {
            'name': _('Payment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request',
            'res_id': self.payment_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }