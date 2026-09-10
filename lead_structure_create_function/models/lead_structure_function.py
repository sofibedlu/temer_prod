from odoo import models, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record.compute_sales_structure()
        record.write({
            'supervisor_id': record.supervisor_id.id,
            'sales_team_id': record.sales_team_id.id,
            'wing_id': record.wing_id.id,
        })

        if hasattr(self.env['crm.activity.report'], 'update_activity_report_copy'):
            self.env['crm.activity.report'].update_activity_report_copy()
        return record