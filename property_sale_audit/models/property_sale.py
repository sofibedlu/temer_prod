from odoo import models, fields, _
from odoo.exceptions import UserError

class PropertySale(models.Model):
    _inherit = 'property.sale'

    state = fields.Selection(
        selection_add=[
            ('check', 'Checked'),
            ('approve',)
        ],
        ondelete={'check': 'set default'}
    )

    def action_audit_sale(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.state = 'check'

    def action_approve_sale(self):
        
        # Block any records that are NOT in the 'check' state
        invalid_records = self.filtered(lambda r: r.state != 'check')
        if invalid_records:
            raise UserError(_("You can only approve contracts that are currently in the 'Checked' state.\n"
                              "Please ensure all selected records have been Checked before approval."))
        

        # To reuse the original logic without rewriting it, temporarily set them to 'confirm'.
        for rec in self:
            rec.state = 'confirm'
            
        return super(PropertySale, self).action_approve_sale()