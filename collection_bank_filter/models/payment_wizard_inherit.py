import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class CollectionPaymentWizard(models.TransientModel):
    _inherit = 'property.payment.register.wizard'

    allowed_bank_ids = fields.Many2many(
    'bank.configuration',
    string="Allowed Banks"
    )

    @api.model
    def default_get(self, fields_list):
        # fetch standard defaults
        res = super(CollectionPaymentWizard, self).default_get(fields_list)
        
        current_user = self.env.user
        site_access_records = self.env['collection.site.access'].sudo().search([('user_id', '=', current_user.id)])
        assigned_site_ids = site_access_records.mapped('site_ids').ids

        if not assigned_site_ids:
            #_logger.info(f"No assigned sites found for user {current_user.name}.")
            return res

        mapping_lines = self.env['site.company.mapping.line'].sudo().search([
            ('site_id', 'in', assigned_site_ids)
        ])
        company_ids = mapping_lines.mapped('company_id').ids

        if not company_ids:
            #_logger.info(f"No developers found for the assigned sites of user {current_user.name}.")
            return res

        valid_banks = self.env['bank.configuration'].sudo().search([
            ('developer_id_bank', 'in', company_ids)
        ])
        
        _logger.info(f"Valid banks for user {current_user.name}: {valid_banks.mapped('bank')}")
        
        if valid_banks:
            res['allowed_bank_ids'] = [(6, 0, valid_banks.ids)]
            
        return res