from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DiscountRequestWizard(models.TransientModel):
    _name = 'discount.request.wizard'
    _description = 'Discount Request Wizard'

    collection_id = fields.Many2one('collection.order', string='Collection Order', required=True, readonly=True)
    currency_id = fields.Many2one(related='collection_id.currency_id')
    installment_id = fields.Many2one('collection.installment', string='Installment', required=True, domain="[('collection_id', '=', collection_id)]")
    
    installment_residual = fields.Monetary(string='Current Residual', related='installment_id.amount_residual')
    discount_percentage = fields.Float(string='Discount (%)', required=True)
    discount_amount = fields.Monetary(string='Calculated Discount', compute='_compute_amounts')
    remaining_amount = fields.Monetary(string='Remaining After Discount', compute='_compute_amounts')
    
    reason = fields.Text(string='Reason', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.depends('discount_percentage', 'installment_id.amount_total', 'installment_id.amount_paid')
    def _compute_amounts(self):
        for rec in self:
            if rec.installment_id:
                base_amount = rec.installment_id.amount_total - rec.installment_id.amount_paid
                rec.discount_amount = base_amount * (rec.discount_percentage / 100.0)
                rec.remaining_amount = base_amount - rec.discount_amount
            else:
                rec.discount_amount = 0.0
                rec.remaining_amount = 0.0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['collection_id'] = active_id
        return res

    def action_submit_request(self):
        self.ensure_one()
        existing = self.env['discount.request'].search([
            ('collection_id', '=', self.collection_id.id),
            ('installment_id', '=', self.installment_id.id),
            ('state', '=', 'pending')
        ])
        if existing:
            raise UserError(_("A pending discount request already exists for this installment."))

        request = self.env['discount.request'].sudo().create({
            'collection_id': self.collection_id.id,
            'installment_id': self.installment_id.id,
            'discount_percentage': self.discount_percentage,
            'reason': self.reason,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'state': 'pending',
        })
        
        # Link attachments to the request
        for att in self.attachment_ids:
            att.write({'res_model': 'discount.request', 'res_id': request.id})
            
        # Trigger the submission
        request.action_submit()
        
        return {'type': 'ir.actions.act_window_close'}