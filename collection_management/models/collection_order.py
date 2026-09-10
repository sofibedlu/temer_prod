from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CollectionOrder(models.Model):
    _name = 'collection.order'
    _description = 'Collection Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(string='Collection Reference', required=True, copy=False, readonly=True, default='New')
    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='sale_id.partner_id', store=True)
    property_id = fields.Many2one('property.property', string='Property', related='sale_id.property_id', store=True)
    payment_schedule_type = fields.Selection(
        [('progress', 'Progress Based'), ('time', 'Time Based')],
        string="Payment Schedule Type",
        compute='_compute_payment_schedule_type',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('void', 'Void')
    ], string='Status', default='draft', tracking=True)

    installment_ids = fields.One2many('collection.installment', 'collection_id', string='Installments')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    total_penalty = fields.Monetary(string='Total Penalty Applied', compute='_compute_total_penalty', store=True, currency_field='currency_id')
    amount_total = fields.Monetary(string='Total Selling Price', related='sale_id.sale_price', store=True)

    amount_collected = fields.Monetary(string='Total Collected', compute='_compute_financials', store=True)
    amount_remaining = fields.Monetary(string='Total Remaining', compute='_compute_financials', store=True)

    contract_number = fields.Char(related='sale_id.contract_number', string='Contract Number', readonly=True)
    sale_ref = fields.Char(string='Sale Reference', related='sale_id.name', store=True)
    site_id = fields.Many2one(
        'property.site', 
        related='sale_id.property_id.site', 
        store=True, 
        string='Property Site'
    )

    @api.depends('sale_id')
    def _compute_payment_schedule_type(self):
        for rec in self:
            if rec.sale_id and 'payment_schedule_type' in rec.sale_id:
                rec.payment_schedule_type = rec.sale_id.payment_schedule_type
            else:
                rec.payment_schedule_type = False

    @api.depends('installment_ids.amount_paid', 'installment_ids.amount_residual', 'amount_total')
    def _compute_financials(self):
        for rec in self:
            rec.amount_collected = sum(rec.installment_ids.mapped('amount_paid'))
            rec.amount_remaining = sum(rec.installment_ids.mapped('amount_residual'))

    @api.depends('installment_ids.penalty_amount', 'installment_ids.penalty_applied')
    def _compute_total_penalty(self):
        for rec in self:
            rec.total_penalty = sum(inst.penalty_amount for inst in rec.installment_ids.filtered(lambda l: l.penalty_applied))

    def _check_and_update_completed_status(self):
        """Checks if all installments are paid and updates state to completed."""
        for rec in self:
            if rec.state == 'active':
                if not any(inst.state != 'paid' for inst in rec.installment_ids):
                    rec.state = 'completed'
                    rec.message_post(body="Collection automatically marked as Completed because all installments are paid.")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('collection.order') or 'New'
        return super(CollectionOrder, self).create(vals)

    def action_open_void_wizard(self):
        return {
            'name': 'Void Contract',
            'type': 'ir.actions.act_window',
            'res_model': 'property.void.wizard', 
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }

    def action_open_transfer_wizard(self):
        return {
            'name': 'Transfer Property',
            'type': 'ir.actions.act_window',
            'res_model': 'property.transfer.wizard', 
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }
    
    def action_open_extension_wizard(self):
        return {
            'name': 'Extend Payment Date',
            'type': 'ir.actions.act_window',
            'res_model': 'property.payment.extension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }
    
    def action_open_apply_penalty_wizard(self):
        return {
            'name': 'Apply Penalty',
            'type': 'ir.actions.act_window',
            'res_model': 'property.penalty.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }
    
    def action_open_sale(self):
        """Open the related Property Sale form."""
        self.ensure_one()
        if not self.sale_id:
            raise UserError("No Property Sale linked to this Collection Order.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.sale',
            'res_id': self.sale_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    