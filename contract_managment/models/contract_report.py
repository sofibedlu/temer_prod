from odoo import models, api

class ContractReport(models.AbstractModel):
    _name = 'report.contract_managment.report_printed_contract_document'
    _description = 'Contract Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # This picks up the 'data' dict you passed from your button
        return {
            'doc_ids': docids,
            'doc_model': 'property.sale',
            'docs': self.env['property.sale'].browse(docids),
            'data': data,  
        }