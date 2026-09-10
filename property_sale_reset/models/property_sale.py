from odoo import models, fields

class PropertySale(models.Model):
    _inherit = 'property.sale'

    skip_contract_generation = fields.Boolean(string="Skip Contract Generation", default=False, copy=False)

    def action_set_to_request_for_confirm(self):
        for rec in self:
            if rec.state not in ['draft', 'void', 'request_for_confirm']:
                rec.state = 'request_for_confirm'
                rec.skip_contract_generation = True