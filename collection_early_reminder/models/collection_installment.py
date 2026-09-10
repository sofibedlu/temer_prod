from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    payment_request_letter_date = fields.Date(
        string="Payment Request Letter Date", 
        compute="_compute_payment_request_letter_date", 
        store=True,
        help="Date exactly one month prior to the actual Due Date."
    )
    
    request_letter_status = fields.Char(
        string="Requested Letters", 
        compute="_compute_request_letter_status",
        help="Shows the number of letters sent or 'Not Requested'."
    )

    @api.depends('due_date')
    def _compute_payment_request_letter_date(self):
        for rec in self:
            if rec.due_date:
                rec.payment_request_letter_date = rec.due_date - relativedelta(months=1)
            else:
                rec.payment_request_letter_date = False

    def _compute_request_letter_status(self):
        for rec in self:
            letters = self.env['letter.saved'].search([
                ('installment_id', '=', rec.id),
                ('letter_type_id.name', 'ilike', 'request')
            ])
            count = len(letters)
            
            if count > 0:
                rec.request_letter_status = f"{count} Requested"
            else:
                rec.request_letter_status = "Not Requested"

    def action_open_collection_order_from_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Collection Order',
            'res_model': 'collection.order',
            'view_mode': 'form',
            'res_id': self.collection_id.id,
            'target': 'current',
        }
