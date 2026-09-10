from odoo import models

class ReportTemerLeadAnalysis(models.AbstractModel):
    _name = 'report.custom_report_wizard.temer_lead_analysis_report_template'
    _description = 'Temer Lead Analysis Report'

    def _get_report_values(self, docids, data=None):
        # If docids is empty, we're likely generating from the wizard action
        if not docids and data:
            # Use the data directly that was passed from the wizard
            return {
                'doc_ids': docids,
                'doc_model': 'temer.lead.analysis.wizard',
                'docs': self.env['temer.lead.analysis.wizard'],
                'data': data,
            }
        
        # If we have docids, get the wizard record and prepare data
        docs = self.env['temer.lead.analysis.wizard'].browse(docids)
        if docs:
            return {
                'doc_ids': docids,
                'doc_model': 'temer.lead.analysis.wizard',
                'docs': docs,
                'data': docs._prepare_report_data(),
            }
        
        # Fallback: return empty data
        return {
            'doc_ids': docids,
            'doc_model': 'temer.lead.analysis.wizard',
            'docs': self.env['temer.lead.analysis.wizard'],
            'data': {},
        }