from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyContractVoidRequest(models.Model):
    _inherit = 'property.contract.void.request'

    state = fields.Selection(
        selection_add=[
            ('checked', 'Checked'),
            ('approved',)
        ],
        ondelete={'checked': 'set default'}
    )
    
    attached_file = fields.Binary(string='Attachment', attachment=True)
    attached_file_name = fields.Char(string='File Name')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # Refund
    pay_date = fields.Date(string="Expected Refund Date", tracking=True)
    penalty_percent = fields.Float(string="Penalty (%)", default=0.0, tracking=True)
    
    currency_id = fields.Many2one('res.currency', related='sale_id.company_id.currency_id')
    collected_amount = fields.Monetary(string="Collected Amount", compute='_compute_refund_amounts', currency_field='currency_id')
    penalty_amount = fields.Monetary(string="Penalty Amount", compute='_compute_refund_amounts', currency_field='currency_id')
    refund_amount = fields.Monetary(string="Refund Amount", compute='_compute_refund_amounts', currency_field='currency_id')
    
    credit_note_id = fields.Many2one('account.move', string="Credit Note", readonly=True)

    @api.depends('penalty_percent', 'sale_id', 'collection_id')
    def _compute_refund_amounts(self):
        for rec in self:
            order = getattr(rec, 'collection_id', False) or (rec.sale_id.collection_order_id if rec.sale_id else False)
            collected = sum(order.installment_ids.mapped('amount_paid')) if order else 0.0
            
            rec.collected_amount = collected
            rec.penalty_amount = (collected * rec.penalty_percent) / 100.0
            rec.refund_amount = collected - rec.penalty_amount

    def action_check(self):
        for record in self:
            if not record.pay_date:
                raise UserError(_("Please set the Expected Refund Date before checking the request."))
            if record.penalty_percent < 0 or record.penalty_percent > 100:
                raise UserError(_("Penalty percentage must be between 0 and 100."))
                
            if record.state == 'draft':
                record.state = 'checked'

    def perform_approval(self):
        res = super(PropertyContractVoidRequest, self).perform_approval()
        
        # Create the Credit Note (Refund) in draft
        # for req in self:
        #     if req.refund_amount > 0 and not req.credit_note_id:
        #         partner = req.partner_id or req.sale_id.partner_id
        #         move_vals = {
        #             'move_type': 'out_refund', # Customer Credit Note
        #             'partner_id': partner.id,
        #             'invoice_date': req.pay_date or fields.Date.context_today(self),
        #             'ref': f"Refund for Voided Request {req.name}",
        #             'is_void_refund': True,
        #             'void_penalty_amount': req.penalty_amount,
        #             'invoice_line_ids': [(0, 0, {
        #                 'name': f"Refund for Voided Contract {req.sale_id.name or ''}",
        #                 'quantity': 1,
        #                 'price_unit': req.refund_amount,
        #             })]
        #         }
        #         move = self.env['account.move'].sudo().create(move_vals)
        #         req.credit_note_id = move.id
                
        # return res