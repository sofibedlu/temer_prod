from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PropertyProperty(models.Model):
    _inherit = 'property.property'

    is_legacy = fields.Boolean(string="Is Legacy Property", default=False)
    
    @api.model
    def _search(self, domain, *args, **kwargs):
        if self._context.get('hide_legacy_properties'):
            domain = (domain or []) + [('is_legacy', '=', False)]
        return super()._search(domain, *args, **kwargs)

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    legacy_created = fields.Boolean(string="Created by Legacy Import", default=False)


class PropertySale(models.Model):
    _inherit = 'property.sale'

    is_legacy = fields.Boolean(string="Is Legacy Record", default=False)
    legacy_contract_number = fields.Char(string="Legacy Contract Number")

    @api.depends('property_id', 'partner_id')
    def compute_sale_rice(self):
        """Override to prevent legacy sales from resetting price/calculating discount."""
        legacy_recs = self.filtered(lambda r: r.is_legacy or r._context.get('legacy_import'))
        normal_recs = self - legacy_recs

        for rec in legacy_recs:
            rec.discount = 0.0
            if not rec.sale_price and rec.property_id:
                rec.sale_price = rec.property_id.unit_price

        # For normal: Run standard logic
        if normal_recs:
            super(PropertySale, normal_recs).compute_sale_rice()

    @api.depends('sale_price', 'discount_line_id', 'total_paid')
    def compute_payment_based_discount(self):
        """Override to prevent payment term discounts on legacy sales."""
        legacy_recs = self.filtered(lambda r: r.is_legacy or r._context.get('legacy_import'))
        normal_recs = self - legacy_recs

        for rec in legacy_recs:
            rec.payment_based_discount = 0.0
            rec.discount_line_id = False

        if normal_recs:
            super(PropertySale, normal_recs).compute_payment_based_discount()

    @api.depends('sale_price', 'discount_line_id', 'total_paid')
    def compute_new_sale_price(self):
        """Override to ensure new_sale_price equals sale_price for legacy."""
        legacy_recs = self.filtered(lambda r: r.is_legacy or r._context.get('legacy_import'))
        normal_recs = self - legacy_recs

        for rec in legacy_recs:
            rec.new_sale_price = rec.sale_price

        if normal_recs:
            super(PropertySale, normal_recs).compute_new_sale_price()

    def add_discount_on_payment_term(self, res):
        """Skip adding discount lines for legacy sales."""
        if res.is_legacy or res._context.get('legacy_import'):
            return
        super(PropertySale, self).add_discount_on_payment_term(res)

    def add__special_discount_on_payment_term(self, res):
        """Skip adding special discount lines for legacy sales."""
        if res.is_legacy or res._context.get('legacy_import'):
            return
        super(PropertySale, self).add__special_discount_on_payment_term(res)

    def compute_sale_payment_line(self):
        real_records = self.filtered(lambda r: isinstance(r.id, int))
        non_legacy_records = real_records.filtered(lambda r: not (r.is_legacy or r._context.get('legacy_import')))
        if non_legacy_records:
            super(PropertySale, non_legacy_records).compute_sale_payment_line()

    def action_confirm(self):
        if self.is_legacy or self._context.get('legacy_import'):
            for rec in self:
                if not rec.legacy_contract_number:
                    raise ValidationError(_("Please provide the Legacy Contract Number for legacy records."))
                rec.write({'state': 'confirm'})
                ContractApp = self.env['contract.application']
                existing_contract = ContractApp.search([('property_sale_id', '=', rec.id)], limit=1)
                if not existing_contract:
                    ContractApp.create({
                        'property_sale_id': rec.id,
                        'name': rec.legacy_contract_number,
                    })
                else:
                    existing_contract.write({
                        'name': rec.legacy_contract_number,
                    })
                if rec.property_id.state != 'sold':
                    rec.property_id.write({'state': 'sold'})
            return True

        return super(PropertySale, self).action_confirm()