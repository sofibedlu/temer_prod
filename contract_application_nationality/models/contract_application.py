from odoo import models, fields

class ContractApplication(models.Model):
    _inherit = 'contract.application'

    nationality_id = fields.Char(string='Nationality')
    place_of_birth = fields.Char(string='Place of Birth')
    passport_id_number = fields.Char(string='Passport/ID')


class ContractPerson(models.Model):
    _inherit = 'contract.person'

    nationality_id = fields.Char(string='Nationality')
    place_of_birth = fields.Char(string='Place of Birth')
    passport_id_number = fields.Char(string='Passport/ID')