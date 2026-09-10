from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        if self.env.context.get('pre_contract_refund_partner_phone_search') and name:
            or_domains = [
                [('name', operator, name)],
                [('ref', operator, name)],
                [('phone', operator, name)],
                [('mobile', operator, name)],
            ]
            if 'phone_no' in self._fields:
                or_domains.append([('phone_no', operator, name)])
            if name.isdigit():
                or_domains.append([('id', '=', int(name))])

            domain = expression.AND([args, expression.OR(or_domains)])
            partners = self.search(domain, limit=limit)
            return partners.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
