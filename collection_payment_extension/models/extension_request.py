from odoo import models, fields, api, _
from markupsafe import Markup

class CollectionPaymentExtensionRequest(models.Model):
    _name = 'collection.payment.extension.request'
    _description = 'Payment Extension Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', default=lambda self: _('New'), readonly=True)
    collection_id = fields.Many2one('collection.order', string='Collection', required=True, readonly=True)
    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    current_date = fields.Date(string='Current Due Date', readonly=True)
    new_date = fields.Date(string='Requested Date', required=True, readonly=True)
    reason = fields.Text(string='Reason', required=True, readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True, string="Status")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('collection.extension.request') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        for rec in self:
            old_date = rec.installment_id.extended_date or rec.installment_id.due_date
            
            # bypass the "changed manually" log note
            rec.installment_id.sudo().with_context(due_date_update_source='extension').write({
                'extended_date': rec.new_date,
                'due_date': rec.new_date,
                'remark': (rec.installment_id.remark or '') + "\n[Extension Approved] %s -> %s : %s" % (old_date, rec.new_date, rec.reason)
            })
            rec.state = 'approved'
            
            msg = Markup("Payment Extension <b>Approved</b> for <b>%s</b><br/>Old Date: %s<br/>New Date: %s<br/>Reason: %s") % (
                rec.installment_id.name, old_date, rec.new_date, rec.reason
            )
            rec.collection_id.sudo().message_post(body=msg)
            
            if hasattr(rec.installment_id, '_compute_state'):
                rec.installment_id.sudo()._compute_state()

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Reject Extension Request',
            'type': 'ir.actions.act_window',
            'res_model': 'extension.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def perform_rejection(self, reason):
        for req in self:
            req.write({'state': 'rejected', 'rejection_reason': reason})
            msg = Markup("Payment Extension <b>Rejected</b> for <b>%s</b><br/>Requested Date: %s<br/>Reason: %s") % (
                req.installment_id.name, req.new_date, reason
            )
            req.collection_id.sudo().message_post(body=msg)