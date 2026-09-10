from odoo import models, fields, api

class BankInherit(models.Model):
    _inherit = 'bank.configuration'

    developer_id_bank = fields.Many2one('site.company', string="Site Company")