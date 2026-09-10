from odoo import models, fields, api, _
from markupsafe import Markup

class PropertyScheduleAmendmentRequest(models.Model):
    _name = 'property.schedule.amendment.request'
    _description = 'Contract Amendment Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', default='New', readonly=True)
    collection_id = fields.Many2one('collection.order', string='Collection Order', required=True, readonly=True)
    sale_id = fields.Many2one('property.sale', related='collection_id.sale_id', string='Property Sale', store=True)
    contract_number = fields.Char(
        string='Contract Number',
        related='sale_id.contract_id.name',
        readonly=True,
        store=True
    )
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)
    current_partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', string='Current Customer', readonly=True)
    new_partner_name = fields.Char(string='New Customer (If changing)', tracking=True)
    is_schedule_change = fields.Boolean(string="Involves Schedule Change", readonly=True, tracking=True)
    reason = fields.Text(string='Reason for Amendment', required=True, tracking=True)
    proposed_changes = fields.Html(string='Proposed Schedule Changes', help="Detailed instructions for the contract team on how to adjust the schedule.")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)

    def action_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Amendment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'amendment.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def perform_rejection(self, reason):
        for req in self:
            req.write({'state': 'rejected', 'rejection_reason': reason})
            if req.collection_id:
                req.collection_id.sudo().message_post(
                    body=Markup("<b>Amendment Request Rejected</b><br/>Request Ref: %s<br/>Reason: %s") % (req.name, reason)
                )
            req.sudo().message_post(body=Markup("<b>Request Rejected</b><br/>Reason: %s") % reason)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('property.schedule.amendment.request') or 'New'
        return super().create(vals_list)
    
    def action_approve(self):
        """Open the confirmation wizard instead of directly approving."""
        self.ensure_one()
        return {
            'name': 'Confirm Amendment Approval',
            'type': 'ir.actions.act_window',
            'res_model': 'amendment.request.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def perform_approval(self):
        for req in self:
            sale = req.sale_id
            
            target_partner = req.new_partner_name if req.new_partner_name else "No Change"
            
            if req.is_schedule_change:
                history = self.env['property.payment.schedule.history'].sudo().create({
                    'sale_id': sale.id,
                    'reason': req.reason,
                })
                
                for line in sale.payment_installment_line_ids:
                    self.env['property.payment.schedule.history.line'].sudo().create({
                        'history_id': history.id,
                        'name': line.payment_term_id.name if line.payment_term_id else 'Installment',
                        'expected_amount': line.expected_amount,
                        'paid_amount': line.paid_amount,
                        'expected': line.expected,
                    })
                sale.sudo().write({'is_schedule_unlocked': True})
                
                sale.sudo().message_post(body=Markup(
                    "<b>Payment Schedule Unlocked for Amendment</b><br/>"
                    "Requested via Collection Order: %s<br/>"
                    "<b>Reason:</b> %s<br/>"
                    "<b>New Customer Requested:</b> %s<br/>"
                    "<b>Instructions:</b> %s"
                ) % (req.collection_id.name, req.reason, target_partner, req.proposed_changes))
                
                req.collection_id.sudo().message_post(body=Markup("<b>Amendment Request Approved</b><br/>The contract schedule is now unlocked and awaiting execution by the contract team."))
            else:
                sale.sudo().message_post(body=Markup(
                    "<b>Contract Amendment Approved (No Schedule Change)</b><br/>"
                    "Requested via Collection Order: %s<br/>"
                    "<b>Reason:</b> %s<br/>"
                    "<b>New Customer Requested:</b> %s"
                ) % (req.collection_id.name, req.reason, target_partner))
                
                req.collection_id.sudo().message_post(body=Markup("<b>Amendment Request Approved</b><br/>The amendment is approved (e.g., Name Change). No schedule unlock was required."))
            
            req.state = 'approved'
            