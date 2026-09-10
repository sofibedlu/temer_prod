from odoo import models, fields,api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class EarlySettlementWizard(models.TransientModel):
    _inherit = 'collection.early.settlement.wizard'

    reason = fields.Text(string='Reason for Request', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    discount_amount = fields.Monetary(
        string='Discount Amount', 
        compute='_compute_calculations', 
        store=True, 
        readonly=False
    )

    @api.onchange('discount_amount')
    def _onchange_discount_amount_manual(self):
        for rec in self:
            if rec.eligible_amount and rec.eligible_amount > 0:
                rec.discount_percentage = (rec.discount_amount / rec.eligible_amount) * 100.0
            else:
                rec.discount_percentage = 0.0

    def action_confirm_settlement(self):
        self.ensure_one()

        config = self.env['collection.discount.config'].sudo().search([], limit=1)
        max_percent = config.max_early_settlement_percentage if config else 10.0
        
        if self.discount_percentage > max_percent:
             raise UserError(_("You cannot request a settlement discount of %s%%. The maximum allowed is %s%%.") % (self.discount_percentage, max_percent))
        
        if self.final_payoff_amount <= 0:
            raise UserError(_("The final payoff amount must be positive."))

        request = self.env['early.settlement.request'].sudo().create({
            'collection_id': self.collection_id.id,
            'total_remaining': self.total_remaining,
            'overdue_amount': self.overdue_amount,
            'eligible_amount': self.eligible_amount,
            'discount_percentage': self.discount_percentage,
            'discount_amount': self.discount_amount,
            'final_payoff_amount': self.final_payoff_amount,
            'reason': self.reason,
            'state': 'pending',
            'attachment_ids': [(6, 0, self.attachment_ids.ids)]
        })

        # history lines for what is being folded
        all_unpaid = self.collection_id.installment_ids.filtered(lambda x: x.state != 'paid' and x.amount_residual > 0)
        history_lines = []
        for inst in all_unpaid:
            history_lines.append((0, 0, {
                'name': inst.name,
                'due_date': inst.due_date,
                'amount_total': inst.amount_total,
                'amount_paid': inst.amount_paid,
                'amount_residual': inst.amount_residual,
                'state': inst.state,
            }))
        request.sudo().write({'history_line_ids': history_lines})

        for att in self.attachment_ids:
            att.sudo().write({'res_model': 'early.settlement.request', 'res_id': request.id})

        msg = Markup("<b>Early Settlement Request Submitted</b><br/>Requested Discount: %s%%<br/>Reason: %s") % (
            self.discount_percentage, self.reason
        )
        self.collection_id.sudo().message_post(body=msg)

        return {'type': 'ir.actions.act_window_close'}