from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PaymentRequest(models.Model):
    _inherit = 'payment.request'
    
    purchase_id = fields.Many2one('purchase.order', string="Source Purchase Order", readonly=True)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    payment_request_ids = fields.One2many('payment.request', 'purchase_id', string='Payment Requests')
    payment_request_count = fields.Integer(compute='_compute_payment_request_count')

    @api.depends('payment_request_ids')
    def _compute_payment_request_count(self):
        for order in self:
            order.payment_request_count = len(order.payment_request_ids)

    def action_view_payment_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Requests',
            'res_model': 'payment.request',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id}
        }

    def action_create_payment_request(self):
        self.ensure_one()
        
        # Calculate how much has already been requested to auto-fill the remaining amount
        active_requests = self.payment_request_ids.filtered(lambda p: p.state not in ['canceled', 'void'])
        requested_amount = sum(active_requests.mapped('amount'))
        remaining_amount = self.amount_total - requested_amount

        if remaining_amount <= 0:
            raise UserError(_("You have already requested payments covering the full amount of this Purchase Order."))

        return {
            'name': _('Create Payment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.payment.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_amount': remaining_amount,
                'default_reason': f"Payment for PO: {self.name}",
            }
        }


class PurchasePaymentRequestWizard(models.TransientModel):
    _name = 'purchase.payment.request.wizard'
    _description = 'Create Payment Request Wizard'

    purchase_id = fields.Many2one('purchase.order', required=True, readonly=True)
    amount = fields.Monetary(string='Amount to Request', required=True)
    percentage = fields.Float(string='Percentage (%)')
    currency_id = fields.Many2one(related='purchase_id.currency_id')
    reason = fields.Text(string='Reason', required=True)

    @api.onchange('percentage')
    def _onchange_percentage(self):
        if self.percentage and self.purchase_id:
            self.amount = (self.percentage / 100.0) * self.purchase_id.amount_total

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount and self.purchase_id and self.purchase_id.amount_total > 0:
            self.percentage = (self.amount / self.purchase_id.amount_total) * 100.0

    def action_confirm_request(self):
        self.ensure_one()
        
        if self.amount <= 0:
            raise UserError(_("Amount must be greater than strictly zero."))
            
        if self.amount > self.purchase_id.amount_total:
            raise UserError(_("You cannot request an amount greater than the Purchase Order total."))

        # Create the Payment Request
        pr = self.env['payment.request'].create({
            'pay_to': 'vendor',
            'partner_id': self.purchase_id.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'reason': self.reason,
            'purchase_id': self.purchase_id.id,
        })
        
        # Post a message on the PO
        self.purchase_id.message_post(
            body=Markup(_("Payment Request <b>%s</b> created for <b>%s %s</b>.")) % (
                pr.pr_number, 
                self.amount, 
                self.currency_id.name
            )
        )
        
        return {'type': 'ir.actions.act_window_close'}