
from odoo import models, fields, api,_

class PropertyCommissionPayment(models.Model):
    _name = 'property.commission.payment'
    sequence = fields.Integer(default=10)
    site_id = fields.Many2one('property.site', string="Site")
    amount_from = fields.Float(string="From(%)")
    amount_to = fields.Float(string="To(%)")
    amount = fields.Float(string="Amount(%)")

    @api.constrains('amount_from','amount_to','amount')
    def validate_amounts(self):
        for rec in self:
            if rec.amount_to>100 or rec.amount_to < 0:
                raise ValidationError("Amount to must be between 0 and 100")
            if rec.amount_from>100 or rec.amount_from < 0:
                raise ValidationError("Amount From must be between 0 and 100")
            if rec.amount>100 or rec.amount < 0:
                raise ValidationError("Amount must be between 0 and 100")
            if rec.amount_from > rec.amount_to:
                raise ValidationError("Amount From must be  > Amount to")


class PropertySiteCommissionLine(models.Model):
    _name = 'property.site.commission.line'

    site_id = fields.Many2one('property.site', string="Site", required=True)
    commission_id = fields.Many2one('property.commission', string="Commission", required=True)
    self_rate = fields.Float('Self Rate', compute='commission_compute_fields')
    type = fields.Char('Type', compute='commission_compute_fields')
    commission = fields.Float('Commission', compute='commission_compute_fields')


    @api.depends('commission_id')
    def commission_compute_fields(self):
        for rec in self:
            rec.self_rate=rec.commission_id.self_rate
            rec.type=rec.commission_id.type
            rec.type=rec.commission_id.type
            rec.commission=rec.commission_id.commission



class PropertySiteCommision(models.Model):
    _name = 'property.site.commission'

    property_sale = fields.Many2one('property.sale')
    partner = fields.Many2one('res.partner')
    commition_type = fields.Many2one('property.commission')
    commission_percentage = fields.Float('Percentage')
    commission_amount = fields.Float('Commission')
    state = fields.Selection(related='property_sale.state', string="State", store=True, readonly=True)
    is_billed = fields.Boolean(default=False)
    bill_state = fields.Boolean(default=False)

    @api.onchange("state","is_invoiced")
    def _onchange_state(self):
        if self.state == 'confirm' and self.is_billed == False:
            self.bill_state = True

    def commission_bill(self):
        """Generate Bills Based on the Monetary Values and return
            Bills Form View"""
        self.write({'is_billed': True})
        return {
            'name': _('Commission Bill'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_move_type': 'in_invoice',
                'default_company_id': self.env.user.company_id.id,
                'default_partner_id': self.property_sale.broker_id.id,
                'default_property_order_id': self.id,
                'default_invoice_line_ids': [fields.Command.create({
                    'name': self.property_sale.name+" for " + self.partner.name +"-"+self.commition_type.name,
                    'price_unit': self.commission_amount,
                    'currency_id': self.env.user.company_id.currency_id.id,
                })]
            }
        }
