from odoo import models, api

class ContractPerson(models.Model):
    _inherit = 'contract.person'

    @api.constrains('contract_id', 'person_type')
    def _check_legal_representative_limit(self):
        pass