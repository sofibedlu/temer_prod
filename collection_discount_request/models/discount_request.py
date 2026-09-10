from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

class DiscountRequest(models.Model):
    _name = 'discount.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Discount Request'
    _order = 'id desc'

    name = fields.Char(string='Reference', default=lambda self: _('New'), readonly=True)
    collection_id = fields.Many2one('collection.order', string='Collection Order', required=True, readonly=True)
    installment_id = fields.Many2one('collection.installment', string='Target Installment', required=True, readonly=True)
    discount_percentage = fields.Float(string='Requested Discount (%)', required=True, readonly=True)
    discount_amount = fields.Monetary(string='Calculated Discount Amount', compute='_compute_discount_amount', store=True, readonly=True)
    remaining_amount = fields.Monetary(string='Remaining After Discount', compute='_compute_discount_amount', store=True, readonly=True)
    reason = fields.Text(string='Reason', required=True, readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, readonly=True)
    currency_id = fields.Many2one(related='collection_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('discount.request')
        return super().create(vals_list)

    @api.depends('discount_percentage', 'installment_id.amount_total', 'installment_id.amount_paid', 'state')
    def _compute_discount_amount(self):
        for rec in self:
            # lock the amounts
            if rec.state in ['approved', 'rejected'] and rec.discount_amount > 0:
                continue
            
            if rec.installment_id:
                base_amount = rec.installment_id.amount_total - rec.installment_id.amount_paid
                rec.discount_amount = base_amount * (rec.discount_percentage / 100.0)
                rec.remaining_amount = base_amount - rec.discount_amount
            else:
                rec.discount_amount = 0.0
                rec.remaining_amount = 0.0

    @api.constrains('discount_percentage')
    def _check_discount_limit(self):
        config = self.env['collection.discount.config'].sudo().search([], limit=1)
        max_percent = config.max_manual_discount_percentage if config else 10.0
        for rec in self:
            if rec.discount_percentage > max_percent:
                raise ValidationError(_("Requested discount (%s%%) exceeds the maximum allowed (%s%%).") % (rec.discount_percentage, max_percent))

    def action_submit(self):
        self.ensure_one()
        self.state = 'pending'
        msg = Markup(
            "<b>Discount Request Submitted</b><br/>"
            "<ul>"
            "<li><b>Request Reference:</b> {}</li>"
            "<li><b>Requested Discount:</b> {:.2f}%</li>"
            "<li><b>Discount Amount:</b> {:.2f}</li>"
            "<li><b>Reason:</b> {}</li>"
            "</ul>"
        ).format(self.name, self.discount_percentage, self.discount_amount, self.reason)
        
        self.collection_id.sudo().message_post(body=msg)

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Only pending requests can be approved."))

        applied_percentage = self.discount_percentage
        applied_amount = self.discount_amount

        self.state = 'approved'
        
        # Apply the discount to the installment
        self.installment_id.sudo().write({'discount_amount': applied_amount})
        
        msg = Markup(
            "<b>Discount Request Approved</b><br/>"
            "<ul>"
            "<li><b>Installment:</b> {}</li>"
            "<li><b>Discount Applied:</b> {:.2f}% ({:.2f})</li>"
            "</ul>"
        ).format(self.installment_id.name, applied_percentage, applied_amount)
        
        self.collection_id.sudo().message_post(body=msg)

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Reject Discount Request',
            'type': 'ir.actions.act_window',
            'res_model': 'discount.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def perform_rejection(self, reason):
        for rec in self:
            rec.write({'state': 'rejected', 'rejection_reason': reason})
            
            msg = Markup(
                "<b>Discount Request Rejected</b><br/>"
                "<ul>"
                "<li><b>Request Reference:</b> {}</li>"
                "<li><b>Reason:</b> {}</li>"
                "</ul>"
            ).format(rec.name, reason)
            
            rec.collection_id.sudo().message_post(body=msg)