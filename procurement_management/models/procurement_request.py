from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup

class ProcurementRequest(models.Model):
    _name = 'procurement.request'
    _description = 'Procurement Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New', readonly=True)
    origin = fields.Char(string='Source Document')
    department_id = fields.Many2one('hr.department', string='Requesting Department')
    date = fields.Date(string='Date', default=fields.Date.context_today, tracking=True)
    expected_date = fields.Date(string='Expected Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('reject', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('procurement.request.line', 'procurement_id', string='Products')
    proforma_count = fields.Integer(compute='_compute_proforma_count', string='Proforma Count')

    evaluation_count = fields.Integer(compute='_compute_evaluation_count', string='Analyses')
    po_count = fields.Integer(compute='_compute_po_count', string='Purchase Orders')

    department_request_id = fields.Many2one(
        'department.request', 
        string='Source Document', 
        compute='_compute_department_request', 
        store=True
    )
    requestor_id = fields.Many2one('res.users', string='Requested By', related='department_request_id.requestor_id')
    checked_by_id = fields.Many2one('res.users', string='Checked By', related='department_request_id.checked_by_id')
    approved_by_id = fields.Many2one('res.users', string='Approved By', related='department_request_id.approved_by_id')

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Very High'),
        ('5', 'Urgent')
    ], string='Priority', default='0', tracking=True)

    @api.depends('origin')
    def _compute_department_request(self):
        for rec in self:
            rec.department_request_id = False
            if rec.origin:
                dept_req = self.env['department.request'].search([('name', '=', rec.origin)], limit=1)
                rec.department_request_id = dept_req.id if dept_req else False

    def action_view_department_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Source Document',
            'res_model': 'department.request',
            'view_mode': 'form',
            'res_id': self.department_request_id.id,
        }
    
    def _compute_proforma_count(self):
        for rec in self:
            rec.proforma_count = self.env['procurement.proforma.analysis'].search_count([
                ('procurement_ids', 'in', rec.id)
            ])
    
    def _compute_evaluation_count(self):
        for rec in self:
            rec.evaluation_count = self.env['procurement.proforma.evaluation'].search_count([
                ('procurement_ids', 'in', rec.id)
            ])

    def _compute_po_count(self):
        for rec in self:
            rec.po_count = self.env['purchase.order'].search_count([
                ('custom_evaluation_id.procurement_ids', 'in', rec.id)
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('procurement.request') or 'New'
        return super().create(vals_list)
    
    def action_request(self):
        for rec in self:
            rec.state = 'requested'
    
    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            if rec.origin:
                dept_request = self.env['department.request'].sudo().search([('name', '=', rec.origin)], limit=1)
                if dept_request:
                    msg = Markup(f"Procurement Request <b>{rec.name}</b> has been <b style='color:green;'>Approved</b>.")
                    dept_request.message_post(body=msg)

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'
            if rec.origin:
                dept_request = self.env['department.request'].sudo().search([('name', '=', rec.origin)], limit=1)
                if dept_request:
                    msg = Markup(f"Procurement Request <b>{rec.name}</b> has been <b style='color:red;'>Rejected</b>.")
                    dept_request.message_post(body=msg)

    def action_create_proforma(self):
        self.ensure_one()
        proforma_vals = {
            'procurement_ids': [(6, 0, [self.id])],
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'product_uom_id': line.product_uom_id.id,
                'specifications': line.specifications,
            }) for line in self.line_ids]
        }
        proforma = self.env['procurement.proforma.analysis'].create(proforma_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Collection',
            'res_model': 'procurement.proforma.analysis',
            'view_mode': 'form',
            'res_id': proforma.id,
            'target': 'current',
        }

    def action_view_proformas(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Collections',
            'res_model': 'procurement.proforma.analysis',
            'view_mode': 'tree,form',
            'domain': [('procurement_ids', 'in', self.id)],
        }
    
    def action_view_evaluations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Analyses',
            'res_model': 'procurement.proforma.evaluation',
            'view_mode': 'tree,form',
            'domain': [('procurement_ids', 'in', self.id)],
        }

    def action_view_pos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('custom_evaluation_id.procurement_ids', 'in', self.id)],
        }

class ProcurementRequestLine(models.Model):
    _name = 'procurement.request.line'
    _description = 'Procurement Request Line'

    procurement_id = fields.Many2one('procurement.request', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Float(default=1.0)
    product_uom_id = fields.Many2one('uom.uom', required=True)
    purpose = fields.Char(string='Purpose/Usage')
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id', 
        string='Product UoM Category'
    )
    technical = fields.Float(string='Technical (%)', default=0.0)
    financial = fields.Float(string='Financial (%)', default=0.0)
    specifications = fields.Html(string='Specifications', sanitize=True)

    @api.constrains('technical', 'financial')
    def _check_technical_financial_total(self):
        for line in self:
            total = round((line.technical or 0.0) + (line.financial or 0.0), 2)
            if total != 100.0:
                raise ValidationError(_("Technical + Financial must equal 100%%."))