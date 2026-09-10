from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.access_control import require_feature

class EarlySettlementWizard(models.TransientModel):
    _name = 'collection.early.settlement.wizard'
    _description = 'Early Settlement Discount Wizard'

    collection_id = fields.Many2one('collection.order', string='Collection Contract', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')
    total_remaining = fields.Monetary(string='Total Remaining Balance', readonly=True)  
    overdue_amount = fields.Monetary(
        string='Overdue Amount (Excluded)', 
        readonly=True, 
        help="Sum of installments that are Overdue or Past Due. These are NOT eligible for discount."
    )
    
    eligible_amount = fields.Monetary(
        string='Eligible for Discount', 
        readonly=True,
        help="Sum of future unpaid installments."
    )
    discount_percentage = fields.Float(string='Discount Percentage (%)', default=5.0)
    discount_amount = fields.Monetary(string='Discount Amount', compute='_compute_calculations')
    final_payoff_amount = fields.Monetary(string='Final Payoff Amount', compute='_compute_calculations')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            collection = self.env['collection.order'].browse(self.env.context['active_id'])
            today = fields.Date.today()

            # Get ALL installments that have a remaining balance (Unpaid + Partial)
            all_unpaid = collection.installment_ids.filtered(lambda x: x.state != 'paid' and x.amount_residual > 0)
            
            # Identify Overdue Installments
            overdue_inst = all_unpaid.filtered(
                lambda x: x.state == 'overdue' or (x.due_date and x.due_date < today)
            )
            overdue_amt = sum(overdue_inst.mapped('amount_residual'))

            # Identify Eligible Installments
            eligible_inst = all_unpaid - overdue_inst
            eligible_amt = sum(eligible_inst.mapped('amount_residual'))

            res.update({
                'collection_id': collection.id,
                'total_remaining': sum(all_unpaid.mapped('amount_residual')),
                'overdue_amount': overdue_amt,
                'eligible_amount': eligible_amt,
            })
        return res

    @api.depends('eligible_amount', 'discount_percentage', 'overdue_amount')
    def _compute_calculations(self):
        for rec in self:
            # Calculate Discount on ELIGIBLE amount only
            discount = rec.eligible_amount * (rec.discount_percentage / 100.0)
            rec.discount_amount = discount
            
            # Final Payoff = Overdue (Full) + (Eligible - Discount)
            rec.final_payoff_amount = rec.overdue_amount + (rec.eligible_amount - discount)

    def action_confirm_settlement(self):
        self.ensure_one()
        require_feature(self.env, "early_settlement", message="You are not allowed to process early settlements.")

        # Check Early Settlement Limit
        config = self.env['collection.discount.config'].sudo().search([], limit=1)
        max_percent = config.max_early_settlement_percentage if config else 10.0
        
        if self.discount_percentage > max_percent:
             raise UserError(_("You cannot apply a settlement discount of %s%%. The maximum allowed is %s%%.") % (self.discount_percentage, max_percent))
        
        if self.final_payoff_amount <= 0:
            raise UserError(_("The final payoff amount must be positive."))

        all_unpaid = self.collection_id.installment_ids.filtered(lambda x: x.state != 'paid' and x.amount_residual > 0)
        for inst in all_unpaid:
            if inst.payment_ids:
                # SAFE MODE: If payments exist, set Total = Paid. This makes Residual = 0 and State = Paid.
                inst.sudo().write({
                    'amount_total': inst.amount_paid,
                    'remark': (inst.remark or '') + "\n[System] Remaining balance moved to Early Settlement."
                })
            else:
                # CLEAN MODE: No payments, safe to delete.
                inst.sudo().unlink()

        # Create the Final Settlement Installment
        self.env['collection.installment'].sudo().create({
            'collection_id': self.collection_id.id,
            'name': f'Early Settlement (Includes {self.discount_percentage}% Discount)',
            'due_date': fields.Date.today(),
            'amount_total': self.final_payoff_amount,
            'remark': f"Settlement of remaining balance.\nOriginal Eligible: {self.eligible_amount}\nDiscount Applied: {self.discount_amount}\nOverdue Included: {self.overdue_amount}"
        })

        # Record the Discount on the Collection Order
        self.collection_id.sudo().message_post(body=f"Early Settlement Applied.\nDiscount: {self.discount_amount}\nPayoff: {self.final_payoff_amount}")
        
        return {'type': 'ir.actions.act_window_close'}