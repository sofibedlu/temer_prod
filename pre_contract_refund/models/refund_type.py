from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyPreContractRefundType(models.Model):
    _name = 'property.pre.contract.refund.type'
    _description = 'Pre Contract Refund Type'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Type', required=True, tracking=True)
    code = fields.Selection(
        [
            ('full_cancellation', 'Full Cancellation'),
            ('overpayment', 'Overpayment'),
        ],
        string='Code',
        required=True,
        default='full_cancellation',
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        (
            'name_uniq',
            'unique(name)',
            'This refund type already exists.',
        ),
        (
            'code_uniq',
            'unique(code)',
            'This refund type code already exists.',
        ),
    ]

    @api.model
    def name_create(self, name):
        type_name = (name or '').strip()
        if not type_name:
            raise ValidationError(_('Refund type is required.'))
        existing = self.search([('name', '=ilike', type_name)], limit=1)
        if existing:
            return existing.name_get()[0]
        raise ValidationError(_('Only configured refund types can be selected.'))

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['property.pre.contract.refund.type']
        for vals in vals_list:
            type_name = (vals.get('name') or '').strip()
            if not type_name:
                raise ValidationError(_('Refund type is required.'))
            if vals.get('code') not in ('full_cancellation', 'overpayment'):
                raise ValidationError(_('Refund type must be Full Cancellation or Overpayment.'))
            existing = self.search([('name', '=ilike', type_name)], limit=1)
            if existing:
                records |= existing
            else:
                record = super(PropertyPreContractRefundType, self).create({
                    **vals,
                    'name': type_name,
                })
                record.message_post(
                    body=_('<b>Refund type created</b><br/>Type: %s') % record.name
                )
                records |= record
        return records
