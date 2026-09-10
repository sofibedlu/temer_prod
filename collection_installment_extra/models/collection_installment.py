from odoo import models, fields, api

try:
    from ethiopian_date import EthiopianDateConverter
except ImportError:
    EthiopianDateConverter = None

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    contract_date_char = fields.Char(
        string='Contract Date (Eth)',
        compute='_compute_contract_date_char',
        store=True,
    )

    ethiopian_due_date = fields.Char(
        string='Due Date-Ethiopian',
        compute='_compute_ethiopian_due_date',
        store=True,
    )

    @api.depends('collection_id.sale_id.contract_id.contract_date_char')
    def _compute_contract_date_char(self):
        for rec in self:
            contracts = rec.collection_id.sale_id.contract_id
            rec.contract_date_char = contracts[0].contract_date_char if contracts else False

    @api.depends('due_date')
    def _compute_ethiopian_due_date(self):
        for rec in self:
            if not rec.due_date or not EthiopianDateConverter:
                rec.ethiopian_due_date = False
                continue
            try:
                eth_date = EthiopianDateConverter.to_ethiopian(
                    rec.due_date.year, rec.due_date.month, rec.due_date.day
                )
                rec.ethiopian_due_date = f"{eth_date.day:02d}/{eth_date.month:02d}/{eth_date.year}"
            except ValueError:
                if rec.due_date.month == 9 and 5 <= rec.due_date.day <= 11:
                    eth_year = rec.due_date.year - 8
                    pagume_day = rec.due_date.day - 5
                    rec.ethiopian_due_date = f"{pagume_day:02d}/13/{eth_year}"
                else:
                    rec.ethiopian_due_date = False