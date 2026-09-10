# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CollectionReportWizard(models.TransientModel):
    """
    Wizard for generating collection reports with filters
    """
    _name = 'collection.report.wizard'
    _description = 'Collection Report Wizard'

    report_type = fields.Selection([
        ('general_info', 'General Information Report'),
        ('summarized', 'Summarized Report'),
        ('plan_stage', 'Plan Based on Collection Stage'),
        ('report_stage', 'Report Based on Collection Stage'),
        ('monthly', 'Monthly Plan/Report'),
    ], string='Report Type', required=True)

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    partner_id = fields.Many2one('res.partner', string='Customer')
    
    def action_generate(self):
        """Generate the report"""
        self.ensure_one()
        
        # Build domain based on filters
        domain = []
        
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        if self.date_from:
            domain.append(('due_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('due_date', '<=', self.date_to))
        
        # Return appropriate action based on report type
        if self.report_type == 'general_info':
            return {
                'type': 'ir.actions.act_window',
                'name': 'General Information Report',
                'res_model': 'collection.order',
                'view_mode': 'tree,form',
                'domain': domain,
                'context': {'search_default_group_by_site': 1},
            }
        else:
            # For other reports, show installments
            return {
                'type': 'ir.actions.act_window',
                'name': 'Collection Report',
                'res_model': 'collection.installment',
                'view_mode': 'tree,form',
                'domain': domain,
            }

