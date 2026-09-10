from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyContractPrintLetterWizard(models.TransientModel):
    _name = 'property.print.letter.wizard'
    _description = 'Print Collection Letter Wizard'

    collection_id = fields.Many2one('collection.order', string="Collection", required=False)
    installment_id = fields.Many2one(
        'collection.installment',
        string='Select Installment',
        required=True,
        domain="[('collection_id','=',collection_id), ('state','!=','paid')]"
    )
    letter_type = fields.Selection([
        ('payment_request', 'Payment Request'),
        ('warning', 'Warning Letter'),
        ('termination', 'Termination Notice'),
    ], string='Letter Type', default='payment_request', required=True)

    letterhead_id = fields.Many2one(
        "collection.letterhead",
        string="Letterhead",
        required=True,
    )

    letter_date = fields.Date(
        string="Letter Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    letter_number = fields.Char(
        string="Letter Number",
        required=True,
    )

    def action_print_letter(self):
        self.ensure_one()
        if not self.letterhead_id:
            raise UserError(_("Please select a Letterhead."))
        
        ctx = dict(
            self.env.context,
            letterhead_id=self.letterhead_id.id,
            letter_date=self.letter_date,
            letter_number=self.letter_number,
        )

        if self.letter_type == 'warning':
            return self.env.ref('collection_management.action_report_warning_letter').with_context(ctx).report_action(self.installment_id)
        elif self.letter_type == 'termination':
            return self.env.ref('collection_management.action_report_termination_letter').with_context(ctx).report_action(self.installment_id)
        else:
            return self.env.ref('collection_management.action_report_collection_letter').with_context(ctx).report_action(self.installment_id)
