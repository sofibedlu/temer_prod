from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertySale(models.Model):
    _inherit = 'property.sale'

    org_unit_id = fields.Many2one('property.org.unit', string="Organizational Unit", tracking=True)

    def request_for_confirmation_action(self):
        """ OVERRIDE: Block the request if no Org Unit is selected. """
        for rec in self:
            if not rec.org_unit_id:
                raise UserError(_("Please select an Organizational Unit before requesting confirmation."))
        return super(PropertySale, self).request_for_confirmation_action()