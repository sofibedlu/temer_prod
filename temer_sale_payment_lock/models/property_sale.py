from odoo import models, fields, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    is_payment_locked = fields.Boolean(
        string="Template Sync Locked", 
        compute="_compute_is_payment_locked",
        store=True,
        readonly=False,
        copy=False,
        tracking=True,
        help="If checked, the installment lines will not be overwritten"
    )

    @api.depends('state')
    def _compute_is_payment_locked(self):
        for sale in self:
            if sale.state in ['confirm', 'approve', 'done']:
                sale.is_payment_locked = True
            else:
                if not sale.is_payment_locked:
                    sale.is_payment_locked = False

    @api.onchange('property_payment_term')
    def recalculate_payment_line_based_on_payment_term(self):
        for rec in self:
            if rec.is_payment_locked:
                return 
        
        if hasattr(super(PropertySale, self), 'recalculate_payment_line_based_on_payment_term'):
            return super(PropertySale, self).recalculate_payment_line_based_on_payment_term()