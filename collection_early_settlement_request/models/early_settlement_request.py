from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class EarlySettlementRequest(models.Model):
    _name = 'early.settlement.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Early Settlement Request'
    _order = 'id desc'

    name = fields.Char(string='Reference', default=lambda self: _('New'), readonly=True)
    collection_id = fields.Many2one('collection.order', string='Collection Contract', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')
    
    total_remaining = fields.Monetary(string='Total Remaining Balance', readonly=True)
    overdue_amount = fields.Monetary(string='Overdue Amount', readonly=True)
    eligible_amount = fields.Monetary(string='Eligible for Discount', readonly=True)
    
    discount_percentage = fields.Float(string='Discount (%)', readonly=True)
    discount_amount = fields.Monetary(string='Discount Amount', readonly=True)
    final_payoff_amount = fields.Monetary(string='Final Payoff Amount', readonly=True)
    
    reason = fields.Text(string='Reason', required=True, readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    history_line_ids = fields.One2many('early.settlement.history', 'request_id', string='Installments to Settle', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('early.settlement.request')
        return super().create(vals_list)

    def action_approve(self):
        for request in self:
            if request.state != 'pending':
                raise UserError(_("Only pending requests can be approved."))
            
            # Execute Settlement Logic (existing code from wizard)
            all_unpaid = request.collection_id.installment_ids.filtered(lambda x: x.state != 'paid' and x.amount_residual > 0)
            
            for inst in all_unpaid:
                if inst.payment_ids:
                    inst.sudo().write({
                        'amount_total': inst.amount_paid,
                        'remark': (inst.remark or '') + "\n[System] Remaining balance moved to Early Settlement."
                    })
                else:
                    inst.sudo().unlink()

            self.env['collection.installment'].sudo().create({
                'collection_id': request.collection_id.id,
                'name': f'Early Settlement (Includes {request.discount_percentage}% Discount)',
                'due_date': fields.Date.today(),
                'amount_total': request.final_payoff_amount,
                'remark': f"Settlement of remaining balance.\nOriginal Eligible: {request.eligible_amount}\nDiscount Applied: {request.discount_amount}\nOverdue Included: {request.overdue_amount}"
            })

            request.write({'state': 'approved'})
            msg = Markup(
                "<b>Early Settlement Request Approved</b><br/>"
                "Discount Applied: %s<br/>"
                "Payoff Amount: %s"
            ) % (request.discount_amount, request.final_payoff_amount)
            request.collection_id.sudo().message_post(body=msg)

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Reject Settlement Request',
            'type': 'ir.actions.act_window',
            'res_model': 'settlement.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def perform_rejection(self, reason):
        for rec in self:
            rec.write({'state': 'rejected', 'rejection_reason': reason})
            msg = Markup("<b>Early Settlement Request Rejected</b><br/>Reason: %s") % reason
            rec.collection_id.sudo().message_post(body=msg)