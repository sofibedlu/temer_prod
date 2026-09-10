from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        # Check if user has permission to create leads
        if not self.env.user.has_group('crm_lead_restriction.group_lead_creator'):
            raise ValidationError(_("You are not allowed to create leads. Please contact your administrator."))
        
        return super(CrmLead, self).create(vals)

    def write(self, vals):
        # Allow writes for existing records, but you can add restrictions here if needed
        return super(CrmLead, self).write(vals)