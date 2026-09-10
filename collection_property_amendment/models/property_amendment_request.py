from odoo import models, fields, api, _
from markupsafe import Markup

class PropertyAmendmentRequest(models.Model):
    _name = 'property.amendment.request'
    _description = 'Property Amendment Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    collection_order_id = fields.Many2one('collection.order', string="Collection Order", readonly=True, tracking=True)
    property_sale_id = fields.Many2one('property.sale', related='collection_order_id.sale_id', string="Property Sale", store=True)
    
    old_property_id = fields.Many2one('property.property', string="Current Property", readonly=True)
    site_id = fields.Many2one('property.site', related='old_property_id.site', string="Site")
    
    new_property_id = fields.Many2one(
        'property.property', 
        string="New Property", 
        required=True, 
        tracking=True,
        domain="[('site', '=', site_id), ('state', '=', 'available')]"
    )
    
    reason = fields.Text(string="Reason for Amendment", tracking=True)
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True, tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        string='Attachments', 
        help="Any documents attached to this amendment request"
    )

    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('checked', 'Checked'),
        ('approved', 'Approved & Transferred'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted', tracking=True)
    show_mark_done = fields.Boolean(compute='_compute_show_mark_done')

    def _compute_show_mark_done(self):
        for req in self:
            req.show_mark_done = self.env.context.get('show_mark_done', False)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.amendment.request') or _('New')
        return super(PropertyAmendmentRequest, self).create(vals)
    
    def action_mark_done(self):
        for req in self:
            req.write({'state': 'done'})
            if req.collection_order_id:
                req.collection_order_id.message_post(
                    body=Markup(f"<b>Property Amendment Finalized ({req.name})</b><br/>Contract team has adjusted the terms and locked the schedule.")
                )
    
    def action_check(self):
        for req in self:
            req.write({'state': 'checked'})
            if req.collection_order_id:
                req.collection_order_id.message_post(
                    body=Markup(f"<b>Property Amendment Checked ({req.name})</b><br/>The request is now waiting for final approval.")
                )

    def action_approve(self):
        self.ensure_one()
        return {
            'name': _('Confirm Property Transfer Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.amendment.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_amendment_request_id': self.id}
        }

    def action_reject(self):
        # Open the Rejection Wizard popup
        return {
            'name': _('Reject Amendment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.amendment.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_amendment_request_id': self.id}
        }