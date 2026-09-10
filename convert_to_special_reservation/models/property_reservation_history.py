# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    show_convert_to_special = fields.Boolean(
        compute='can_convert_to_special',
        string="Show Convert to Special Button"
    )
    converted_special = fields.Boolean(
        readonly=True,
        default=False,
        string="Converted to Special Reservation",
        store=True,
        help="Indicates if this reservation was converted from regular/quick to special"
    )

    def action_convert_to_special(self):
        """
        Convert regular/quick reservation to special reservation.
        Follows the same logic as when manually setting is_special_reservation = True.
        
        Logic (matches special_reservation module behavior):
        - Sets is_special_reservation = True
        - Changes reservation_type_id to quick (special reservations use quick type)
        - MAINTAINS current status (same as onchange('is_special_reservation')):
          * If status is 'reserved' → stays 'reserved' (already reserved, just converting type)
          * If status is 'draft' → stays 'draft' (can request special approval later)
        - Property state handling:
          * If status is 'reserved' → property stays 'reserved'
          * If status is 'draft' → property state is NOT changed (remains available/draft)
        
        This matches the normal special reservation flow where:
        - When is_special_reservation is checked, only reservation_type_id changes to 'quick'
        - Status remains unchanged (draft stays draft, reserved stays reserved)
        - Property state matches the status
        """
        for rec in self:
            # Check if special reservation module is installed
            special_module = self.env['ir.module.module'].search([
                ('name', '=', 'special_reservation'),
                ('state', '=', 'installed')
            ], limit=1)
            if not special_module:
                raise ValidationError(_("Special Reservation module is not installed. Please install it first."))
            
            # Find quick reservation type (special reservations use quick type based on special_reservation module logic)
            quick_type = self.env['property.reservation.configuration'].search(
                [('reservation_type', '=', 'quick')], limit=1)
            if not quick_type:
                raise ValidationError(_("No quick reservation type configuration found."))
            
            # Store current status to maintain it
            current_status = rec.status
            
            # Prepare write values - exactly like the onchange('is_special_reservation') logic
            # Only changes reservation_type_id, status remains unchanged
            write_vals = {
                'reservation_type_id': quick_type.id,
                'converted_special': True,
            }
            
            # Set special reservation fields (same as when is_special_reservation checkbox is checked)
            if hasattr(rec, 'is_special_reservation'):
                write_vals['is_special_reservation'] = True
            # Note: make_special_reservation is set to True only when requesting approval,
            # not when just converting to special, so we don't set it here
            
            # Write the values - status remains unchanged (draft stays draft, reserved stays reserved)
            rec.write(write_vals)
            
            # Handle property state based on status (matches special reservation flow):
            # - If status is 'reserved': property should be 'reserved'
            # - If status is 'draft': property state is NOT changed (stays available/draft)
            if rec.property_id:
                if current_status == 'reserved':
                    # Keep property reserved (already reserved, just converting type)
                    if rec.property_id.state not in ['sold', 'pending_sale', 'rented', 'draft']:
                        rec.property_id.sudo().write({'state': 'reserved'})
                # If status is 'draft', do NOT change property state
                # This matches the special reservation flow where draft reservations don't reserve the property
                # until approval is requested
    
    def can_convert_to_special(self):
        """
        Compute method to determine if "Convert to Special" button should be shown.
        """
        for rec in self:
            # Show button if:
            # 1. Reservation type is 'regular' or 'quick'
            # 2. Status is 'reserved' or 'draft'
            # 3. Not already converted to special
            # 4. Not already converted to regular (converted_regular must be False)
            # 5. Special reservation module is installed
            # 6. Not already a special reservation
            special_module_installed = self.env['ir.module.module'].search([
                ('name', '=', 'special_reservation'),
                ('state', '=', 'installed')
            ], limit=1)
            
            # Check if already special reservation (if field exists)
            is_already_special = False
            if hasattr(rec, 'is_special_reservation'):
                is_already_special = rec.is_special_reservation
            if hasattr(rec, 'make_special_reservation') and not is_already_special:
                is_already_special = rec.make_special_reservation
            
            # Check if converted to regular (if field exists)
            converted_to_regular = False
            if hasattr(rec, 'converted_regular'):
                converted_to_regular = rec.converted_regular
            
            rec.show_convert_to_special = (
                bool(special_module_installed)
                and rec.reservation_type_id
                and rec.reservation_type_id.reservation_type in ['regular', 'quick']
                and rec.status in ['reserved', 'draft']
                and not rec.converted_special
                and not converted_to_regular  # Don't show if already converted to regular
                and not is_already_special
            )

