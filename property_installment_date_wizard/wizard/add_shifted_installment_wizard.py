from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class AddShiftedInstallmentWizard(models.TransientModel):
    _name = 'add.shifted.installment.wizard'
    _description = 'Add Shifted Installment Wizard'

    sale_id = fields.Many2one('property.sale', string="Property Sale", required=True, readonly=True)
    
    base_date = fields.Date(string="Base Reference Date", default=fields.Date.context_today, required=True, help="e.g., Contract Signature Date")
    shift_days = fields.Integer(string="Shift (Days)", default=45, required=True, help="Number of days to add to the base date.")
    
    calculated_date = fields.Date(string="Calculated Due Date", compute="_compute_calculated_date", readonly=True)
    amharic_preview = fields.Char(string="Generated Milestone Name", compute="_compute_amharic_preview", readonly=True)

    @api.depends('base_date', 'shift_days')
    def _compute_calculated_date(self):
        for rec in self:
            if rec.base_date:
                rec.calculated_date = rec.base_date + relativedelta(days=rec.shift_days)
            else:
                rec.calculated_date = False

    @api.depends('calculated_date')
    def _compute_amharic_preview(self):
        config = self.env['property.ethiopian.calendar.config'].search([], limit=1)
        for rec in self:
            if rec.calculated_date and config:
                rec.amharic_preview = config.convert_date_to_amharic(rec.calculated_date)
            else:
                rec.amharic_preview = ""

    def action_confirm_add(self):
        self.ensure_one()

        config = self.env['property.ethiopian.calendar.config'].search([], limit=1)
        if not config:
            config = self.env['property.ethiopian.calendar.config'].create({})

        amharic_name = config.convert_date_to_amharic(self.calculated_date)

        parent_term_id = self.sale_id.property_payment_term.id if self.sale_id.property_payment_term else False
        term_line = self.env['property.payment.term.line'].search([('name', '=', amharic_name)], limit=1)
        if not term_line:
            term_line = self.env['property.payment.term.line'].create({
                'name': amharic_name,
                #'payment_term_id': parent_term_id
            })

        existing_lines = self.sale_id.payment_installment_line_ids
        next_sequence = max(existing_lines.mapped('sequence')) + 10 if existing_lines else 10

        self.env['property.payment.line'].create({
            'sale_id': self.sale_id.id,
            'payment_term_id': term_line.id,
            'due_date': self.calculated_date,
            'expected': 0.0,
            'expected_amount': 0.0,
            'sequence': next_sequence
        })

        return True