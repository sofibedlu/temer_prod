from odoo import models, fields, api


class EthiopianBank(models.Model):
    _name = 'ethiopian.bank'
    _description = 'Ethiopian Bank'

    name = fields.Char(string="Bank Name", required=True, unique=True)


class EthiopianBankAccount(models.Model):
    _name = 'ethiopian.bank.account'
    _description = 'Ethiopian Bank Account'
    
    bank_id = fields.Many2one('ethiopian.bank', string="Bank", required=True)
    account_number = fields.Char(string="Account Number", required=True)
