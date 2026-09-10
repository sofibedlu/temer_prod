# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BulkEditLineWizard(models.TransientModel):
    _name = 'bulk.edit.line.wizard'
    _description = 'Edit bulk registration line'

    line_id = fields.Many2one('property.bulk.registration.line', string='Line', required=True, ondelete='cascade')
    site_floor_ids = fields.Many2many(related='line_id.bulk_id.site_floor_ids', readonly=True)
    unit_number = fields.Char(string='House Number', required=True)
    floor_id = fields.Many2one('property.floor', string='Floor', ondelete='restrict',
                               domain="[('id', 'in', site_floor_ids)]")
    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
    ], string='Type')
    commercial_location = fields.Selection([
        ('inside', 'Inside'),
        ('outside', 'Outside'),
    ], string='Site Location')

    price_per_m2_override = fields.Float(string='Price (m²)')
    estimated_sales_price_override = fields.Monetary(string='Estimated Sales Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id', readonly=True)

    property_type_bedroom = fields.Integer(string='Number of bed room')
    property_type_bathroom = fields.Integer(string='Number of bath room')
    property_type_has_maid_room = fields.Boolean(string='Has maid room')
    property_type_gross_area = fields.Float(string='Gross Area')
    property_type_net_area = fields.Float(string='Net area')
    finishing = fields.Selection([
        ('sumi_finished', 'Semi Finished'),
        ('fully_finished', 'Fully Finished'),
        ('none', 'None'),
    ], string='Finishing')

    def action_save(self):
        self.ensure_one()
        line = self.line_id
        ptype = self.property_type if self.property_type else line.property_type
        line.write({
            'unit_number': self.unit_number,
            'floor_id': self.floor_id.id if self.floor_id else line.floor_id.id,
            'property_type': ptype,
            'commercial_location': self.commercial_location if ptype == 'commercial' else False,
            'price_per_m2_override': self.price_per_m2_override if self.price_per_m2_override else (self.line_id.bulk_id.price_per_m2 if self.line_id.bulk_id else 0.0),
            'estimated_sales_price_override': self.estimated_sales_price_override or 0.0,
            'property_type_bedroom': self.property_type_bedroom,
            'property_type_bathroom': self.property_type_bathroom,
            'property_type_has_maid_room': self.property_type_has_maid_room,
            'property_type_gross_area': self.property_type_gross_area,
            'property_type_net_area': self.property_type_net_area,
            'finishing': self.finishing,
            'gross_area': self.property_type_gross_area,
            'net_area': self.property_type_net_area,
            'bedroom': self.property_type_bedroom,
            'bathroom': self.property_type_bathroom,
            'has_maid_room': self.property_type_has_maid_room,
        })
        # Close wizard and reload bulk form
        if line.bulk_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'property.bulk.registration',
                'res_id': line.bulk_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
