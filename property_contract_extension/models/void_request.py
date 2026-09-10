from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import UserError

class PropertyContractVoidRequest(models.Model):
    _name = 'property.contract.void.request'
    _description = 'Void Contract Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', default='New', readonly=True)
    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True, readonly=True)
    property_id = fields.Many2one('property.property', related='sale_id.property_id', string='Property', readonly=True)
    contract_number = fields.Char(related='sale_id.contract_id.name', string='Contract Number', readonly=True)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', string='Customer', readonly=True)
    reason = fields.Text(string='Reason for Voiding', required=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True, string='Status')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('property.contract.void.request') or 'New'
        return super().create(vals_list)
    
    def action_approve(self):
        """Open the confirmation wizard instead of directly approving."""
        self.ensure_one()
        return {
            'name': 'Confirm Void Approval',
            'type': 'ir.actions.act_window',
            'res_model': 'void.request.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def perform_approval(self):
        author_id = self.env.user.partner_id.id

        for req in self:
            # Make property available
            if req.property_id:
                req.property_id.sudo().write({'state': 'available'})
            
            # Change sale state to void
            if req.sale_id:
                req.sale_id.sudo().write({'state': 'void'})

                 # Log approval to Property Sale
                sale_msg = Markup(
                    "<b>Void Request Approved</b><br/>"
                    "Request Ref: %s<br/>"
                    "Reason: %s<br/>"
                    "Contract state changed to Void."
                ) % (req.name, req.reason or 'N/A')
                req.sale_id.sudo().message_post(body=sale_msg, author_id=author_id)
                
                # Void the related Collection Order
                if req.sale_id.collection_order_id:
                    req.sale_id.collection_order_id.sudo().write({'state': 'void'})

                    # Log to Collection Order Chatter
                    req.sale_id.collection_order_id.sudo().message_post(
                        body=Markup("<b>Collection Voided</b><br/>"
                                    "Void Request (%s) was approved.<br/>") % (req.name),
                        author_id=author_id
                    )
                
                # Free up the contract number by appending '-VOID' safely
                if req.sale_id.contract_id:
                    for contract in req.sale_id.contract_id.sudo():
                        old_name = contract.name
                        base_void_name = f"{old_name}-VOID"
                        new_name = base_void_name
                        counter = 1
                        
                        while self.env['contract.application'].sudo().search_count([('name', '=', new_name)]):
                            new_name = f"{base_void_name}-{counter}"
                            counter += 1
                            
                        contract.sudo().write({'name': new_name})
                        
            req.state = 'approved'
    
    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Reject Void Request',
            'type': 'ir.actions.act_window',
            'res_model': 'void.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_void_request_id': self.id}
        }
    
    def perform_rejection(self, reason):
        for req in self:
            req.write({
                'state': 'rejected',
                'rejection_reason': reason
            })
            
            # Log rejection to Property Sale
            if req.sale_id:
                req.sale_id.sudo().message_post(
                    body=Markup("<b>Void Request Rejected</b><br/>"
                                "Request Ref: %s<br/>"
                                "Reason: %s<br/>"
                                "The contract remains active.") % (req.name, reason),
                )
            
            # Log rejection to Void Request Chatter
            req.sudo().message_post(
                body=Markup("<b>Request Rejected</b><br/>"
                            "Reason: %s") % reason,
            )
    
    def action_view_sale(self):
        """Open the related property.sale form view"""
        self.ensure_one()
        if not self.sale_id:
            raise UserError(_("No related Property Sale to open."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Property Sale'),
            'res_model': 'property.sale',
            'res_id': self.sale_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


from odoo import models, fields, api

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    collection_state = fields.Selection(related='collection_id.state', string='Collection State')