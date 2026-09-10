from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.converter import to_ethiopian, to_gregorian

class PostSalesRefundRequest(models.Model):
    _inherit = 'post.sales.refund.request'

    pay_date_eth = fields.Char(string="Expected Refund Date (E.C)", help="Format: dd/mm/yyyy")

    @api.onchange('pay_date')
    def _onchange_pay_date(self):
        if self.pay_date:
            self.pay_date_eth = to_ethiopian(self.pay_date)
        else:
            self.pay_date_eth = False

    @api.onchange('pay_date_eth')
    def _onchange_pay_date_eth(self):
        if self.pay_date_eth:
            try:
                self.pay_date = to_gregorian(self.pay_date_eth)
            except UserError as e:
                return {
                    'warning': {
                        'title': _('Invalid Format'),
                        'message': str(e)
                    }
                }
        else:
            self.pay_date = False