from odoo import models, fields, api, _

class ContractOverrideWizard(models.TransientModel):
    _name = 'contract.override.wizard'
    _description = 'Manual Contract Override Wizard'

    sale_id = fields.Many2one('property.sale', string="Property Sale", readonly=True)
    property_payment_term = fields.Many2one('property.payment.term', string="Payment Term")
    line_ids = fields.One2many('contract.override.wizard.line', 'wizard_id', string="Payment Lines")

    @api.model
    def default_get(self, fields_list):
        res = super(ContractOverrideWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if not active_id:
            return res

        sale = self.env['property.sale'].browse(active_id)
        res['sale_id'] = sale.id
        res['property_payment_term'] = sale.property_payment_term.id

        preview_vals = []
        for line in sale.payment_installment_line_ids.sorted(key=lambda l: l.sequence):
            preview_vals.append((0, 0, {
                'sequence': line.sequence,
                'sale_line_id': line.id,
                'payment_term_id': line.payment_term_id.id,
                'expected': line.expected,
                'expected_amount': line.expected_amount,
                'discount': getattr(line, 'discount', 0.0),
                'paid_amount': line.paid_amount,
                'state': line.state,
            }))

        res['line_ids'] = preview_vals
        return res

    def action_confirm_override(self):
        self.ensure_one()
        sale = self.sale_id

        # Update Term
        sale.sudo().write({'property_payment_term': self.property_payment_term.id})

        # Update, Create, and Delete Lines
        kept_line_ids = []
        for w_line in self.line_ids:
            vals = {
                'sequence': w_line.sequence,
                'payment_term_id': w_line.payment_term_id.id,
                'expected': w_line.expected,
                'expected_amount': w_line.expected_amount,
                'discount': w_line.discount,
                'paid_amount': w_line.paid_amount,
                'state': w_line.state,
            }

            if w_line.sale_line_id:
                w_line.sale_line_id.sudo().write(vals)
                kept_line_ids.append(w_line.sale_line_id.id)
            else:
                vals['sale_id'] = sale.id
                new_line = self.env['property.payment.line'].sudo().create(vals)
                kept_line_ids.append(new_line.id)

        lines_to_delete = sale.payment_installment_line_ids.filtered(lambda l: l.id not in kept_line_ids)
        if lines_to_delete:
            lines_to_delete.sudo().unlink()

        return {'type': 'ir.actions.act_window_close'}


class ContractOverrideWizardLine(models.TransientModel):
    _name = 'contract.override.wizard.line'
    _description = 'Contract Override Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('contract.override.wizard', ondelete='cascade')
    sale_line_id = fields.Many2one('property.payment.line', string="Original Line")
    
    sequence = fields.Integer(string="Sequence", default=10)
    payment_term_id = fields.Many2one('property.payment.term.line', string="Milestone / Term", required=True)
    
    expected = fields.Float(string="Expected (%)")
    expected_amount = fields.Float(string="Expected Amount")
    discount = fields.Float(string="Discount")
    paid_amount = fields.Float(string="Paid Amount")
    
    state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partial'),
        ('paid', 'Paid')
    ], string="State", default='not_paid')

    remaining = fields.Float(string="Remaining", compute="_compute_remaining")

    @api.depends('expected_amount', 'discount', 'paid_amount')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = rec.expected_amount - rec.discount - rec.paid_amount

    @api.onchange('expected')
    def _onchange_expected(self):
        for rec in self:
            if rec.wizard_id and rec.wizard_id.sale_id:
                base_price = rec.wizard_id.sale_id.sale_price - rec.wizard_id.sale_id.discount
                if base_price:
                    rec.expected_amount = (rec.expected * base_price) / 100.0

    @api.onchange('expected_amount')
    def _onchange_expected_amount(self):
        for rec in self:
            if rec.wizard_id and rec.wizard_id.sale_id:
                base_price = rec.wizard_id.sale_id.sale_price - rec.wizard_id.sale_id.discount
                if base_price:
                    rec.expected = (rec.expected_amount / base_price) * 100.0