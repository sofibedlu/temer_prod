from odoo import models, fields, _
from odoo.exceptions import UserError

class PropertyContractPrintLetterWizard(models.TransientModel):
    _inherit = 'property.print.letter.wizard'

    letter_type = fields.Selection(selection_add=[('custom', 'Custom Template')], ondelete={'custom': 'set default'})
    custom_template_id = fields.Many2one(
        'collection.letter.template', 
        string='Template Name',
    )

    def action_print_letter(self):
        self.ensure_one()
        
        if self.letter_type != 'custom':
            return super().action_print_letter()

        if not self.letterhead_id:
            raise UserError(_("Please select a Letterhead."))
        if not self.custom_template_id:
            raise UserError(_("Please select a Custom Template."))
            
        ctx = dict(
            self.env.context,
            letterhead_id=self.letterhead_id.id,
            letter_date=self.letter_date,
            letter_number=self.letter_number,
            custom_template_id=self.custom_template_id.id
        )

        return self.env.ref('collection_letter_template.action_report_dynamic_collection_letter')\
            .with_context(ctx).report_action(self.installment_id)