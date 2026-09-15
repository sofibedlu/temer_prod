from odoo import models, fields, api, _

class CollectionPaidInstallmentSummary(models.TransientModel):
    _name = 'collection.paid.installment.summary'
    _description = 'Paid Installments Summary'

    site_id = fields.Many2one('property.site', string="Site / Project")
    
    site_payment_structure_id = fields.Many2one(
        'property.payment.term', 
        related='site_id.payment_structure_id'
    )

    payment_term_line_id = fields.Many2one(
        'property.payment.term.line', 
        string="Installment (Milestone)"
    )

    installment_ids = fields.Many2many(
        'collection.installment',
        string="Paid Installments",
        compute='_compute_installments_and_total'
    )

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    total_paid_amount = fields.Monetary(
        string="Global Total Paid", 
        compute="_compute_installments_and_total",
        currency_field="currency_id"
    )

    @api.onchange('site_id')
    def _onchange_site_clear_milestone(self):
        """ Clears the milestone dropdown if changes the site """
        if self.site_id and self.payment_term_line_id:
            if self.payment_term_line_id.payment_term_id.id != self.site_id.payment_structure_id.id:
                self.payment_term_line_id = False

    @api.depends('site_id', 'payment_term_line_id')
    def _compute_installments_and_total(self):
        for rec in self:
            domain = [
                ('state', '=', 'paid'),
                ('collection_id.state', '!=', 'void'),
            ]

            if rec.site_id:
                domain.append(('site_id', '=', rec.site_id.id))
            
            if rec.payment_term_line_id:
                domain.append(('name', '=', rec.payment_term_line_id.name))

            if not rec.site_id and not rec.payment_term_line_id:
                rec.installment_ids = False
                rec.total_paid_amount = 0.0
            else:
                installments = self.env['collection.installment'].search(domain)
                rec.installment_ids = installments
                
                rec.total_paid_amount = sum(installments.mapped('amount_paid'))

    @api.model
    def action_open_summary(self):
        record = self.create({})
        return {
            'name': _('Paid Installments Summary'),
            'type': 'ir.actions.act_window',
            'res_model': 'collection.paid.installment.summary',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }