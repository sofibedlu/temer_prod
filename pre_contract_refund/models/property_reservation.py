from odoo import api, fields, models
from odoo.osv import expression


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    pre_contract_refunded = fields.Boolean(
        string='Pre-Contract Refunded',
        default=False,
        copy=False,
        tracking=True,
        help='Checked after a pre-contract full cancellation refund is paid.',
    )

    def _get_pre_contract_refund_display_name(self):
        self.ensure_one()
        status_labels = dict(self._fields['status']._description_selection(self.env))
        customer_name = self.partner_id.display_name or ''
        property_name = self.property_id.display_name or self.property_id.name or ''
        reservation_type = self.reservation_type_id.display_name or ''
        status_name = status_labels.get(self.status, self.status or '')

        parts = [p for p in (customer_name, reservation_type, property_name, status_name) if p]
        return ' - '.join(parts) if parts else f'Reservation #{self.id}'

    @api.depends('partner_id', 'reservation_type_id', 'property_id', 'status')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._get_pre_contract_refund_display_name()

    def name_get(self):
        return [(rec.id, rec._get_pre_contract_refund_display_name()) for rec in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        domain = args
        if name:
            search_terms = [
                [('partner_id.name', operator, name)],
                [('partner_id.ref', operator, name)],
                [('partner_id.phone', operator, name)],
                [('partner_id.mobile', operator, name)],
                [('property_id.name', operator, name)],
                [('property_id.code', operator, name)],
                [('reservation_type_id.name', operator, name)],
            ]
            if name.isdigit():
                numeric = int(name)
                search_terms.extend([
                    [('id', '=', numeric)],
                    [('partner_id.id', '=', numeric)],
                ])
            search_domain = expression.OR(search_terms)
            domain = expression.AND([args, search_domain])
        records = self.search(domain, limit=limit)
        return records.name_get()
