from odoo import models, fields

class PropertySale(models.Model):
    _inherit = 'property.sale'

    updated_pending_approval = fields.Boolean(
        string="Needs Approval Review",
        default=False,
        help="Checked automatically when sale details are updated prior to approval."
    )

    def write(self, vals):
        if not self.env.context.get('skip_approval_flag'):
            vals['updated_pending_approval'] = True
            
        return super(PropertySale, self).write(vals)

    def action_approve_sale(self):
        res = super(PropertySale, self).action_approve_sale()
        self.with_context(skip_approval_flag=True).write({'updated_pending_approval': False})
        return res


class ContractApplication(models.Model):
    _inherit = 'contract.application'

    def write(self, vals):
        res = super(ContractApplication, self).write(vals)
        for record in self:
            if hasattr(record, 'property_sale_id') and record.property_sale_id and not self.env.context.get('skip_approval_flag'):
                record.property_sale_id.with_context(skip_approval_flag=True).write({
                    'updated_pending_approval': True
                })
        return res


class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    def write(self, vals):
        res = super(PropertyPaymentLine, self).write(vals)
        for record in self:
            if record.sale_id and not self.env.context.get('skip_approval_flag'):
                record.sale_id.with_context(skip_approval_flag=True).write({
                    'updated_pending_approval': True
                })
        return res