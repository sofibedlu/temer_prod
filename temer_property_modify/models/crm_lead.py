from odoo.exceptions import ValidationError
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)



class PropertySite(models.Model):
    _inherit = 'property.site'

    floor_id = fields.Many2one(
        'property.floor', string='Floor Number #'
    )
    block_number = fields.Integer(string="Number of block", tracking=True)
    house_number_floor = fields.Integer(string="Number of House Per Floor", tracking=True)

    stock_number = fields.Float(
        string='Stoock Number',
        compute='_compute_stock_number',
        store=False
    )
    description_content = fields.Html(string='Descriptions')

    @api.depends('property_type_lin_ids')
    def _compute_stock_number(self):
        """Alternative implementation using search_count"""
        for site in self:
            site.stock_number = self.env['property.property'].search_count([
                ('site', '=', site.id)
            ])

    def action_view_properties(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Properties in {self.name}',
            'res_model': 'property.property',
            'view_mode': 'tree,form',
            'domain': [('site', '=', self.id)],
            'context': {
                'default_site': self.id,
                'search_default_site_id': self.id
            }
        }



class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    def compute_expected_amount(self):
        """Calculate the expected payment amount based on payment type."""
        self.ensure_one()
        if self.reservation_type_id.payment_type == "fixed":
            return self.reservation_type_id.amount

        # Calculate percentage-based amount
        if self.property_id.is_multi:
            payment_term_line = self.env['property.payment.term.line'].search(
                [('payment_term_id', '=', self.property_id.site_payment_structure_id.payment_term_id.id)],
                order='sequence', limit=1)
        else:
            payment_term_line = self.env['property.payment.term.line'].search(
                [('payment_term_id', '=', self.property_id.payment_structure_id.id)],
                order='sequence', limit=1)

        expected_per = payment_term_line.percentage if payment_term_line else 0
        base_amount = (self.property_id.unit_price
                       if self.property_id.sale_rent == "for_sale"
                       else self.property_id.rent_month)
        return (base_amount * expected_per / 100) * (self.reservation_type_id.amount / 100)
