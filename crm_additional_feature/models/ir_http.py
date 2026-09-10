from odoo import models, api
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'
    
    @classmethod
    def _get_action(cls, key, request):
        """Override to redirect CRM actions"""
        action = super(IrHttp, cls)._get_action(key, request)
        
        # Redirect main CRM action to opportunities list view
        if action and action.get('id') == request.env.ref('crm.crm_lead_action').id:
            return request.env.ref('crm.crm_lead_action_opportunities').read()[0]
        
        return action