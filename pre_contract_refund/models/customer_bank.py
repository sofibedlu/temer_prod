from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyCustomerBank(models.Model):
    _name = 'property.customer.bank'
    _description = 'Bank Name'
    _order = 'bank_name, id desc'
    _rec_name = 'bank_name'

    bank_name = fields.Char(string='Bank Name', required=True)

    _sql_constraints = [
        (
            'bank_name_uniq',
            'unique(bank_name)',
            'This bank name already exists.',
        ),
    ]

    @api.model
    def name_create(self, name):
        bank_name = (name or '').strip()
        if not bank_name:
            raise ValidationError(_('Bank name is required.'))
        existing = self.search([('bank_name', '=ilike', bank_name)], limit=1)
        if existing:
            return existing.name_get()[0]
        record = self.create({'bank_name': bank_name})
        return record.name_get()[0]

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['property.customer.bank']
        for vals in vals_list:
            bank_name = (vals.get('bank_name') or '').strip()
            if not bank_name:
                raise ValidationError(_('Bank name is required.'))
            existing = self.search([('bank_name', '=ilike', bank_name)], limit=1)
            if existing:
                records |= existing
            else:
                records |= super(PropertyCustomerBank, self).create({
                    **vals,
                    'bank_name': bank_name,
                })
        return records


class PropertyCustomerBankDetail(models.Model):
    _name = 'property.customer.bank.detail'
    _description = 'Customer Bank Detail for Refund'
    _order = 'bank_name, account_number, id desc'
    _rec_name = 'account_number'
    _rec_names_search = ['bank_name', 'account_number']

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade',
        index=True,
    )
    bank_name = fields.Char(string='Bank Name', required=True)
    account_number = fields.Char(string='Account Number', required=True)
    active = fields.Boolean(default=True)

    def name_get(self):
        return [(rec.id, rec.account_number or '') for rec in self]
