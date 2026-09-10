from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class InternalRequest(models.Model):
    _name = 'internal.request'
    _description = 'Internal Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New', readonly=True)
    requestor_id = fields.Many2one('res.users', string='Requested By', readonly=True)
    checked_by_id = fields.Many2one('res.users', string='Checked By', readonly=True, tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    rejected_by_id = fields.Many2one('res.users', string='Rejected By', readonly=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)
    expected_date = fields.Date(string='Expected Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Very High'),
        ('5', 'Urgent')
    ], string='Priority', default='0', tracking=True)
    
    @api.model
    def _default_department(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.department_id.id if employee else False
        
    department_id = fields.Many2one('hr.department', string='Requesting Department', required=True, default=_default_department)
    responsible_department_id = fields.Many2one('hr.department', string='Responsible Department', required=True)
    line_ids = fields.One2many('internal.request.line', 'request_id', string='Materials')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('internal.request') or 'New'
        return super().create(vals_list)

    def action_request(self):
        for record in self:
            record.state = 'requested'
            record.requestor_id = self.env.user.id
    
    def action_check(self):
        for record in self:
            record.state = 'checked'
            record.checked_by_id = self.env.user.id

    def action_approve(self):
        for record in self:
            record.state = 'approved'
            record.approved_by_id = self.env.user.id
            dept_vals = {
                'origin': record.name,
                'priority': record.priority,
                'expected_date': record.expected_date,
                'department_id': record.responsible_department_id.id,
                'state': 'draft',
                'line_ids': [(0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'product_uom_id': line.product_uom_id.id,
                    'purpose': line.purpose,
                }) for line in record.line_ids]
            }
            self.env['department.request'].create(dept_vals)

    def action_reject(self):
        for record in self:
            record.state = 'rejected'
            record.rejected_by_id = self.env.user.id

class InternalRequestLine(models.Model):
    _name = 'internal.request.line'
    _description = 'Internal Request Line'

    request_id = fields.Many2one('internal.request', string='Request', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    purpose = fields.Char(string='Purpose/Usage', required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id', 
        string='Product UoM Category'
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0.0:
                raise ValidationError(_("Quantity must be greater than zero."))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id