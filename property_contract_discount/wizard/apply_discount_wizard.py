from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ApplyDiscountWizard(models.TransientModel):
    _name = 'property.apply.discount.wizard'
    _description = 'Apply Discount to Installments'

    sale_id = fields.Many2one('property.sale', string='Property Sale', required=True)
    discount_percentage = fields.Float(string='Discount (%)', required=True)
    
    line_ids = fields.One2many(
        'property.apply.discount.wizard.line', 
        'wizard_id', 
        string='Installments'
    )

    @api.onchange('discount_percentage')
    def _onchange_discount_percentage(self):
        for line in self.line_ids:
            if line.previous_amount:
                line.discount_amount = line.previous_amount * self.discount_percentage

    def action_apply_discount(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please select at least one installment line to apply the discount."))
        
        updated_installments = []
            
        for line in self.line_ids:
            if line.payment_line_id.state in ['paid']:
                raise UserError(_("You cannot apply a discount to already paid or partially paid installments."))

            if line.new_amount < 0:
                raise UserError(_("New amount cannot be negative for installment: %s") % line.payment_line_id.payment_term_id.name)
            
            line.payment_line_id.write({
                #'discount': (line.payment_line_id.discount or 0.0) + line.discount_amount,
                'discount': line.discount_amount,
                'expected_amount': line.new_amount,
                'expected_is_net': True,
            })

        inst_name = line.payment_line_id.payment_term_id.name or line.payment_line_id.display_name or "Installment"
        updated_installments.append(inst_name)
            
        display_percentage = self.discount_percentage * 100
        installments_str = ", ".join(updated_installments)
        self.sale_id.message_post(body=f"Applied {display_percentage:g}% discount to: {installments_str}.")
        return {'type': 'ir.actions.act_window_close'}


class ApplyDiscountWizardLine(models.TransientModel):
    _name = 'property.apply.discount.wizard.line'
    _description = 'Discount Wizard Line'

    wizard_id = fields.Many2one('property.apply.discount.wizard', string='Wizard', ondelete='cascade')
    payment_line_id = fields.Many2one(
        'property.payment.line', 
        string='Installment', 
        domain="[('sale_id', '=', parent.sale_id)]",
        required=True
    )
    
    previous_amount = fields.Float(string='Previous Amount', compute='_compute_amounts', store=True)
    discount_amount = fields.Float(string='Discount Amount')
    new_amount = fields.Float(string='New Amount', compute='_compute_new_amount', store=True)

    @api.depends('payment_line_id')
    def _compute_amounts(self):
        for rec in self:
            rec.previous_amount = rec.payment_line_id.expected_amount if rec.payment_line_id else 0.0

    @api.depends('previous_amount', 'discount_amount')
    def _compute_new_amount(self):
        for rec in self:
            rec.new_amount = rec.previous_amount - rec.discount_amount