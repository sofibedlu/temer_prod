from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyPreContractRefundReason(models.Model):
    _name = 'property.pre.contract.refund.reason'
    _description = 'Pre Contract Refund Reason'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Reason', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        (
            'name_uniq',
            'unique(name)',
            'This refund reason already exists.',
        ),
    ]

    @api.model
    def name_create(self, name):
        reason_name = (name or '').strip()
        if not reason_name:
            raise ValidationError(_('Refund reason is required.'))
        existing = self.search([('name', '=ilike', reason_name)], limit=1)
        if existing:
            return existing.name_get()[0]
        return self.create({'name': reason_name}).name_get()[0]

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['property.pre.contract.refund.reason']
        for vals in vals_list:
            reason_name = (vals.get('name') or '').strip()
            if not reason_name:
                raise ValidationError(_('Refund reason is required.'))
            existing = self.search([('name', '=ilike', reason_name)], limit=1)
            if existing:
                records |= existing
            else:
                record = super(PropertyPreContractRefundReason, self).create({
                    **vals,
                    'name': reason_name,
                })
                record.message_post(
                    body=_('<b>Refund reason created</b><br/>Reason: %s') % record.name
                )
                records |= record
        return records
