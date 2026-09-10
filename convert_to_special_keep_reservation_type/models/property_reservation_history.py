# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import ValidationError


class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    def action_convert_to_special(self):
        """
        Convert regular/quick reservation to special without changing its type.
        """
        for rec in self:
            special_module = self.env['ir.module.module'].search([
                ('name', '=', 'special_reservation'),
                ('state', '=', 'installed')
            ], limit=1)
            if not special_module:
                raise ValidationError(_("Special Reservation module is not installed. Please install it first."))

            current_status = rec.status
            write_vals = {
                'converted_special': True,
            }

            if hasattr(rec, 'is_special_reservation'):
                write_vals['is_special_reservation'] = True

            rec.write(write_vals)

            if rec.property_id and current_status == 'reserved':
                if rec.property_id.state not in ['sold', 'pending_sale', 'rented', 'draft']:
                    rec.property_id.sudo().write({'state': 'reserved'})
